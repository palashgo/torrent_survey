from django.db import models

# Create your models here.

class Movies(models.Model):
    tmdb_id = models.CharField(max_length=12,unique=True)
    title = models.CharField(max_length=1023)
    release_date = models.DateTimeField()
    language = models.CharField(max_length=4)

    def __str__(self):
        return self.title

class Torrent(models.Model):
    movie = models.ForeignKey(Movies,on_delete=models.CASCADE)
    title = models.CharField(max_length=1023)
    full_magnet = models.TextField()
    hash = models.CharField(max_length=64,unique=True)
    size = models.CharField(max_length=16)
    date_uploaded = models.DateTimeField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_quality(self):
        quality = ""
        return quality

class TorrentHistory(models.Model):
    torrent = models.ForeignKey(Torrent,on_delete=models.CASCADE)
    seeds = models.IntegerField()
    peers = models.IntegerField()
    datetime = models.DateTimeField(auto_now_add=True)

class Peers(models.Model):
    torrent = models.ForeignKey(Torrent,on_delete=models.CASCADE)
    ip = models.CharField(max_length=64)
    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True,blank=True)

    class Meta:
        unique_together = ('torrent','ip')



    
