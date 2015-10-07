# Priprava programovaciho modulu #

Kazdy programovaci modul ma 2 rozdilne vetve "zivota". Prvni z nich je **spusteni kodu**, ktere ulohu nevyhodnocuje a pouze umozni uzivateli si spustit kod a neco vygenerovat. Vystupem teto vetve je 1) `stdout` sandboxu v pripade, ze dobehl s nulovym navratovym kodem nebo `stderr` v pripade selhani, 2) v nekterych ulohach obrazek. V druhe vetvi, ktera jiz ulohu **vyhodnocuje** je ignorovano generovani obrazku a uzivateli je vracena pouze informace *dobre*/*spatne*.

Pro spravne pripraveni programovaci modulu, je nutne vytvoritt skript pro kazdy krok workflow (volitelne i post-triggeru) a spravne zpracovat predavane parametry.

## 1. Merge skript ##

**Vstup:** soubor s uzivatelskym kodem

**Vystup:** skript pripraveny ke spusteni

**Parametry:** `<uzivatelsky_kod> <soubor_pro_ulozeni_finalniho_kodu>`

**Sloupce v DB:** `merge_script`

V tomto kroku by melo dojit k doplneni uzivatelskeho kodu o nezbytne hlavicky, paticky, atd. a jeho ulozeni do specifikovaneho souboru. Tento skript by v idealnim pripade mel vzdy skoncit s nulovym navratovym kodem bez chyb. Pokud by se nejaka chyba vyskytla a proces skoncil s nenulovym kodem, je v pripade spusteni kodu jeho spousteni ukonceno s chybovym kodem *1* a v pripade vyhodnoceni je udeleno 0 bodu.

**Ukazka:**
```
import sys

infile = open(sys.argv[1], 'r')
outfile = open(sys.argv[2], 'w')

outfile.write('print \'This is header\'\n')
outfile.write(infile.read())
outfile.write('print \'This is footer\'\n')
outfile.close()
```

## 2. Spusteni v sandboxu ##
**Vstup:** soubor s kodem, umisteni sandboxu, argumenty, stdin, timeout

**Vystup:** stdout, stderr a pripadne ulozene soubory

V tomto kroku neni nutne pripravit zadny skript, protoze sandbox je predpripraveny a nepotrebuje zadnou specialni obsluhu. Proto je treba pouze pripravit soubor reprezentujici `stdin` (klasicky textovy soubor) a seznam argumentu, ktere budou predany spoustenemu skriptu. Aby se usnadnilo jejich zpracovani, je nutne je do DB zadat ve formatu "python-like" seznamu (tim se poresi jejich spravne predani).

Dale je mozne take specifikovat limity, ktere bude mit sandbox tak, aby nemohlo dojit k umyslnemu pretizeni stroje.

Velmi dulezita je take slozka sandboxu, ktera bude namapovana jako `/tmp` adresar spusteneho skriptu a pri spravnem nastaveni PyPy by mohla byt i zapisovatelna pro spusteny proces. Z toho duvodu by mela byt pouzivana pro **veskere vystupy** uzivatelskeho skriptu!

**Ukazka argumentu:**
`[ 'jeden', 'dva', 's mezerou', '--pomlckou', 'a', '--rovnitkem=hodnota' ]`

## 3. Post-trigger ##
**Vstup:** slozka sandboxu

**Vystup:** obrazek, JSON informujici o jeho jmenu

**Argumenty:** `<slozka_sanboxu>`

Toto je jediny nepovinny krok vyhodnoceni a jeho cilem je poskytnout moznost vygenerovat obrazek/cokoliv. Sva data muze cerpat ze slozky sandboxu (tzn. je nutna synchronizace s generujici patickou) a vystupem by krome souboru mel byt take JSON vypsany na `stdout`, ktery obsahuje o nich informace.

Take pozor na to, ze tento krok je volan pouze pri *spousteni kodu* a nikoliv jeho vyhodnocovani!i

**POZOR:** Jelikoz je aktualne pozadavek pouze na jeden obrazek, tak je bran v potaz vzdycky pouze prvni soubor ve vystupnim JSONu a ostatni jsou pripadne zahazovany!

**Priklad vystupniho JSONu:**
```
{
	'attachments': [ 'out.jpg', ...]
}
```

## 4. Vyhodnoceni ulohy ##

**Vstup:** stdout sandboxu, slozka sandboxu

**Vystup:** -

**Argumenty:** `<slozka_sandboxu> <stdout_sandboxu>`

Skript zajistujici vyhodnoceni ulohy. Na zaklade jeho navratoveho kodu je rozhodnuto o spravnosti reseni (0 -> OK, jinak NOK). K dispozici ma jak celou slozku sandboxu (se vsemi soubory), tak stdout sandboxu, ktery muze obsahovat potrebne vystupy.

Tato cast se vola pouze pri vyhodnocovani ulohy. Pri pouhem *spusteni kodu* neni provedena.

