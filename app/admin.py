from django.contrib import admin
from app.models import *
# Register your models here.


@admin.register(Movies)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('title','release_date')

@admin.register(Torrent)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('title','date_added','size')

@admin.register(TorrentHistory)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('torrent','seeds','datetime')

@admin.register(Peers)
class AuthorAdmin(admin.ModelAdmin):
    list_filter = ('torrent__movie',)
    list_display = ('torrent','ip')