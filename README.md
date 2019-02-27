# Bard

Bard is a all-in-one PVR for tracking, downloading and processing TV shows on a recurring basis. The motivation behind Bard is to help tame the ingest of media (specifically TV) into personal libraries like Plex. By tracking the shows you watch Bard can automatically download, extract and process new episodes sourced from your favorite torrent site.

- Simple HTML5/CSS Web UI (read: no javascript/bloat)
- Fetch content in resolutions and codecs that fit your libraries needs
- Lightweight contained webserver (data can be stored in sqlite, tasks can be scheduled via cron)

## Status

Bard is primarily developed for my personal use case and thus has various rough edges for the common user. That said, Bard was designed in a way that makes it extremely pluggable with different torrent trackers, clients and media libraries. Ideally in the future Bards collection of "providers" (implementations of third party services) can be expanded and curated to provide an out of the box solution to more users.

## Installation

Eventually I hope to have a proper guide, but for now you just need to install Bard inside a venv (based on the requirements file), and then run `./manage.py serve`.

## Screenshots

### Series Overview

![](https://i.imgur.com/AstV0dC.png)

### Episodes Overview

![](https://i.imgur.com/4lT6QuA.png)

### Torrents Overview

![](https://i.imgur.com/KR5EE9y.png)

### Series Details

![](https://i.imgur.com/KRXXkkg.png)

### Episode Details

![](https://i.imgur.com/uMSRygd.png)
