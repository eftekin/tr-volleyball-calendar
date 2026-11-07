# voleybol-takvim

TRT Spor ve TRT Spor Yıldız'da yayınlanan kadın voleybol maçlarını (Sultanlar Ligi, Kupa Voley) Google Takvim'e abone olunabilir takvim olarak verir. Maç saatleri ve kanallar [TVF fikstüründen](https://fikstur.tvf.org.tr) anlık çekilir.

## Abone olma

calendar.google.com → Diğer takvimler → **+** → URL'den:

```
https://voleybol-takvim.vercel.app/kadin-voleybol.ics
```

## Geliştirme

```sh
python3 api/ics.py    # takvimi ekrana basar
npx vercel --prod     # yayınlar
```
