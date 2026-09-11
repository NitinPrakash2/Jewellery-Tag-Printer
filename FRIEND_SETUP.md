# Dost ke PC par App Chalana (Doosre Sheher Wala Setup)

> Ye guide usko bhejo jiske paas printer hai. Usko commands nahi chalane —
> sirf 3 cheez install karni hai, phir 2 file double-click karni hai.

## Dost ko kya bhejna hai

Poora `Jewellery-Tag-Printer` folder ka ZIP — **in cheezon ko chhod ke**
(zip chhota rahega, ye sab uske PC par ban jayengi):

- `client/node_modules/`
- `.git/`
- `server/app_data/`, `server/logs/`
- `__pycache__/` folders kahin bhi hon
- `client/dist/` (setup khud bana lega)

## Dost ke PC par (ek baar, 15 minute)

**Step 1 — 3 install (internet chahiye):**

| Kya | Kahan se | Note |
|---|---|---|
| Python 3.13 | python.org/downloads | Install me **"Add python.exe to PATH"** tick zarur karna |
| PostgreSQL 16+ | postgresql.org/download/windows | Install me jo password rakho wo yaad rakhna |
| Node.js 20+ | nodejs.org | Bas Next-Next |

**Step 2 — Setup (double-click):**

1. ZIP kholo (jaise `C:\Jewellery-Tag-Printer`)
2. `server` folder me **`setup-first-time.bat`** double-click karo
3. PostgreSQL wala password mango to likh do — ye sab khud karega:
   libraries install → database → tables → app screen build
4. Last me **"SETUP COMPLETE!"** ayega. Bas, ye file dobara kabhi nahi chalani.

**Step 3 — Printer lagao:**

1. Printer USB se lagao + power on
2. `server` folder me **`start-lan.bat`** double-click karo (roz yahi chalana hai)
3. Jo address dikhe (jaise `http://192.168.1.5:8000`) browser me kholo
   (dusre laptop se bhi same WiFi par yehi address khul jayega)
4. Settings → printer select (DCode khud select ho jayega) → **Run Setup** → **Test Print**

Pehli baar Windows pooche to **Firewall me Allow** kar dena (ya `allow-lan.ps1`
Admin me ek baar chala dena) — taaki dusre laptop jud payen.

## Roz ka istemal (dukandaar)

1. `start-lan.bat` chalao
2. Browser me address kholo
3. Details bharo → **Print Tag** → kagaz nikalo

## Agar atke to

- App me **HELP** tab kholo — poora guide pictures jaisi steps me hai
- Settings me **Live Error Monitor** ka screenshot bhej do — turant pata chal jayega dikkat app me hai ya printer me
