from django_cron import CronJobBase, Schedule
import json
import requests
import re
import datetime
import pytz
from django.db import IntegrityError
import libtorrent as lt
import time
import sys
from .simpletpb import *
from .models import Torrent,Movies,Peers,TorrentHistory
import difflib
from threading import Thread,BoundedSemaphore

threadLimiter = BoundedSemaphore(4)

# Create your views here.

PEER_LIST_WAIT_SEC = 15
MOVIE_PAGE_DEPTH = 4
NOMETADATA_WAIT_SEC = 15

    
class FetchNewMovies(CronJobBase):
    RUN_EVERY_MINS = 960

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'app.FetchNewMoviesJob'

    def do(self):
        for page in range(MOVIE_PAGE_DEPTH):
            movies = requests.get("https://api.themoviedb.org/3/discover/movie?api_key=329bd036bcb58a4646b84ef24e8b6542&with_original_language=hi&sort_by=release_date.desc&page="+str(page+1))
            movies = json.loads(movies.text)['results']
            print(len(movies))
            for m in movies:
                release_date = datetime.datetime.strptime(m['release_date'],"%Y-%m-%d")
                try:
                    movie = Movies.objects.create(tmdb_id=m['id'],title=m['title'],release_date=release_date,language=m['original_language'])
                    movie.save()
                except IntegrityError:pass
            print("New DB movie count",Movies.objects.count())


class FetchNewTorrents(CronJobBase):

    def add_torrents(self,movie,torrents_arr):
        for t in torrents_arr:
            tor = None
            try:
                tor = Torrent.objects.get(hash=t.hash)
            except:
                extracted_title = re.sub("\W"," ",t.extracted_info['title']).lower()
                orignal_title = re.sub("\W"," ",movie.title).lower()
                similarity = difflib.SequenceMatcher(None, extracted_title, orignal_title).ratio()

                if "year" not in t.extracted_info.keys():
                    if similarity > 0.8:
                        tor = Torrent.objects.create(movie=movie,title=t.title,hash=t.hash,full_magnet=t.magnet,date_uploaded=t.uploaded_time,size=t.size)
                        tor.save()
                elif similarity > 0.7 and movie.release_date.year == t.extracted_info['year']:
                    tor = Torrent.objects.create(movie=movie,title=t.title,hash=t.hash,full_magnet=t.magnet,date_uploaded=t.uploaded_time,size=t.size)
                    tor.save()
                    
                else:
                    print(orignal_title,extracted_title,similarity)
            
            if tor:
                tor_history = TorrentHistory.objects.create(torrent=tor,seeds=t.seeds,peers=t.peers)
                tor_history.save()
        
class FetchNewTorrentsFast(FetchNewTorrents):
    RUN_EVERY_MINS = 120
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'app.FetchNewTorrentsFastJob' 

    def do(self):
        movies = Movies.objects.filter(release_date__lt=datetime.datetime.now()).order_by('-release_date')[:20]
        for movie in movies:
            search_result = TPBSearch(movie.title).result
            self.add_torrents(movie,search_result)
                 
class FetchNewTorrentsComplete(FetchNewTorrents):
    RUN_EVERY_MINS = 960 # every 16 hours

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'app.FetchNewTorrentsCompleteJob'  

    def do(self):
        movies = Movies.objects.filter(release_date__lt=datetime.datetime.now()).order_by('-release_date')
        for movie in movies:
            search_result = TPBSearch(movie.title).result
            self.add_torrents(movie,search_result)

class FindAndPeers(Thread) :
    def __init__(self,torrent):
        super(FindAndPeers, self).__init__()
        self.torrent = torrent

    def run(self):
        threadLimiter.acquire()
        try:
            self._run()
        finally:
            threadLimiter.release()

    def _run(self):
        ses = lt.session()
        ses.listen_on(6851, 6891)
        params = {'save_path': '/tmp/'}
        h = lt.add_magnet_uri(ses, self.torrent.full_magnet, params)
        print('starting', h.name())
        peers = []
        tobreak = 0
        nometadata = 0
        while (not h.is_seed()):
            s = h.status()
            peers = h.get_full_peer_list()
            if tobreak == PEER_LIST_WAIT_SEC or nometadata == NOMETADATA_WAIT_SEC:
                break
            if h.has_metadata():
                tobreak += 1
            else:
                nometadata += 1
            time.sleep(1)
        print(len(peers),"found")
        
        for peer in peers:
            try:
                p = Peers.objects.create(torrent=self.torrent,ip=peer)
                p.save()
            except IntegrityError:pass

class FetchPeers(CronJobBase):
    RUN_EVERY_MINS = 120

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'app.FetchPeersJob'

    def do(self):
        torrents = Torrent.objects.all()
        tpool = []
        for t in torrents:
            tsthread = FindAndPeers(t)
            tsthread.start()
            tpool.append(tsthread)
            time.sleep(1)
        for i in tpool:
            i.join()   

