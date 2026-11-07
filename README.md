# voleybol-takvim

> Maçları seçip takvimine eklemek için: **https://voleybol-takvim.vercel.app**

Subscribable calendar of Turkish women's volleyball matches (Sultanlar Ligi, Kupa Voley) with kick-off times and TV channels, pulled live from the [TVF fixture site](https://fikstur.tvf.org.tr). The site and calendar text are in Turkish since that is who watches these matches.

## Calendar link

```
https://voleybol-takvim.vercel.app/kadin-voleybol.ics?lig=Sultanlar+Ligi&kanal=TRT+Spor&takim=VAKIFBANK
```

`lig` (league), `kanal` (channel) and `takim` (team) can each repeat; a group left out is not filtered, and `?lig=` alone gives every match. A link with no filters gives TRT matches only, kept for early subscribers.

## Development

```sh
python3 test_ics.py          # tests, no network
python3 api/ics.py 'lig='    # print the calendar, argument is the link query
npx vercel --prod            # deploy
```

TVF is fetched at most once an hour per warm instance and the CDN caches each link for an hour.
