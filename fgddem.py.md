fgddem.py
=========

概要
----
国土地理院の基盤地図情報 数値標高モデル JPGIS(GML)形式をGeoTIFFに変換するPythonスクリプト。

基盤地図情報サイト: http://www.gsi.go.jp/kiban/index.html

動作環境
--------
WindowsではOSGeo4Wでgdal-pythonパッケージをインストールしておく。
Linuxではpython-gdalパッケージをインストールしておく。
いずれもpythonのバージョン 2.6以上が必要。

インストール・操作方法
----------------------

* バッチファイルへのドラッグ&ドロップによる方法(Windowsのみ)
 1. fgddem.py.droptarget.batをテキストエディタで開き，2行目のOSGEO4W_ROOTの値をOSGeo4Wがインストールされているフォルダパスに変更する。
 2. 国土地理院のダウンロードサイトからダウンロードしたZIPファイルをfgddem.py.droptarget.batにドラッグ&ドロップする。

* コマンドラインでの入力による方法(Windowsの場合)
 1. fgddem.pyとfgddem.py.batをパスの通ったフォルダにコピーする。OSGeo4Wでgdal-pythonをインストールした場合はOSGeo4W\binフォルダにコピーすればよい。
 2. OSGeo4W Shellで次のようにコマンドを入力する。
 `fgddem -out_dir out downloads\FG-*.zip`

コマンドの説明
--------------
`fgddem.py [-replace_nodata_by_zero][-out_dir output_directory] src_files`

GeoTIFFファイルは入力ファイルと同じファイルタイトルで出力される。

* `src_files`:

 JPGIS(GML)形式のXMLファイルまたはそれを含むZIPファイル。ZIPファイルを指定した時は含まれるメッシュがすべて結合されて出力される。複数指定も可能で，ワイルドカードを用いた場合マッチするファイル毎にGeoTIFFファイルが出力される。

* `-replace_nodata_by_zero`:

 このオプションを指定した場合，「データなし」の値が0に置き換えられます。「データなし」の値は設定されません。
このオプションを指定しなければ「データなし」として-9999が設定されます。

* `-out_dir`:

 出力先フォルダ。指定がないときは入力ファイルと同じフォルダに出力される。

更新履歴
--------

* 2014/08/01 Version 0.5 コードの整理。
* 2014/01/28 Version 0.4 実行終了時に生じることのあったエラーを修正。
* 2013/12/15 Version 0.3 基盤地図情報DEMデータファイルの更新に対応。コードの整理。
* 2012/12/18 Version 0.2 非ASCII文字を含むファイルパスのサポート。
* 2012/06/11 Version 0.1 データ読込時間短縮。fgddem_droptarget.batに対する複数ファイルのドラッグ&ドロップ。

**ベータ版**

* 2012/04/18 データ読込時間短縮。
* 2012/04/15 Bounds値の精度改良(10mメッシュ標高にかかわる変更)。
* 2012/04/14 gdal_merge.pyの実行改良。
* 2012/04/08 GDAL>=1.9ではgdal_merge.pyを使用して結合。
* 2012/03/30 `-out_dir`オプションの追加。
* 2012/03/29 `-replace_nodata_by_zero`オプションの追加。結合コマンドをgdalwarpに変更( 2012/4/8で再変更あり)。fgddem_droptarget.batを追加。
* 2012/03/28 metaデータXMLファイルを含むZIPファイルへの対応。gdal_merge.pyの実行改良。
* 2012/03/19 出力メタ情報修正。
* 2012/03/13 進捗状況表示，`-v`オプション等の追加。
* 2012/03/12 fgddem.bat修正。
* 2012/03/10 公開。

_Copyright (c) 2013, Minoru Akagi_
