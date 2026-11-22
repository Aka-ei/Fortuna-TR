# Katkıda bulunma

- Çeviri işleminde aşağıdaki şartla AI kullanabilirsiniz.

- AI Çevirisi kullanılan yerlerin commit edilmeden önce bir insan tarafından [redakte](https://tr.wikipedia.org/wiki/Redaksiyon) edilmesi **zorunludur**.

# Düzenleme

MSBT.zst dosyalarını düzenlemek için [MSBT editor](https://gitlab.com/AeonSake/msbt-editor) programını kullanın. Program otomatik bir şekilde çıkartıp düzenlemenize izin verecektir. Attribute'lar için Fortuna.gcf'yi programın configs klasörüne yükleyin.

bffnt.zst dosyaları için önce [PeaZip](https://peazip.github.io/) ile çıkarttıktan sonra [BFFNT Font Editor](https://github.com/Tarik366/bffnt-font-editor/tree/bffnt-nx2-font-editor) ile düzenleyip PeaZip ile tekrardan sıkıştırın.

# İlerleme

İlerleme tablosunu güncellemek için terminalde ana klasörde aşağıdaki komutu çalıştırın. İlk çalıştırmadan önce `pip install -r requirements.txt` yapmayı unutmayın.

``` powershell
python .\scripts\report_all.py .\romfs\Msg\EUen\ .\romfs\Msg\USen
```
