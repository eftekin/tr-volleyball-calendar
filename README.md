# voleybol-takvim

Kadın voleybol maçlarını (Sultanlar Ligi, Kupa Voley) Google Takvim'e abone olunabilir takvim olarak verir. Maç saatleri ve kanallar [TVF fikstüründen](https://fikstur.tvf.org.tr) anlık çekilir.

## Abone olma

https://voleybol-takvim.vercel.app adresinde lig, kanal ve takım seç, çıkan linki takvimine ekle.

Link elle de kurulabilir; her parametre tekrarlanabilir, boş bırakılan grup filtrelenmez:

```
/kadin-voleybol.ics?lig=Sultanlar+Ligi&kanal=TRT+Spor&kanal=TRT+Spor+Yıldız&takim=VAKIFBANK
```

Parametresiz link sadece TRT maçlarını verir (eski aboneler için).

## Geliştirme

```sh
python3 api/ics.py 'lig='   # takvimi ekrana basar, argüman link parametreleri
npx vercel --prod           # yayınlar
```
