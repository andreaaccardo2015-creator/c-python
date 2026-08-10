# Download Windows

Repo pubblico **solo setup** (niente codice):

https://github.com/andreaaccardo2015-creator/cpython-setup

Release: **`CPython_Setup.exe`** → doppio click → installa.

Poi, in un nuovo terminale:

```bat
cpy version
cpy run tuoFile.cpy
```

Il codice sorgente resta in `c-python` (sviluppo). Per gli utenti finali usa solo `cpython-setup`.

## L'antivirus segnala il file?

È un falso positivo noto degli eseguibili PyInstaller non firmati: il programma
è open source con licenza MIT e la build è pubblica. In
[ANTIVIRUS.md](../ANTIVIRUS.md) trovi la spiegazione tecnica, l'elenco completo
delle modifiche al sistema, come verificare l'hash SHA256 del file e come
sbloccarlo o segnalare l'errore al produttore dell'antivirus.
