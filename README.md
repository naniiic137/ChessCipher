# ChessCipher

A steganographic encryption system that hides secret messages inside realistic chess board images. The message is encoded in the **filename** as standard chess move notation (PGN), and the board image acts as visual camouflage — filled with decoy pieces so nobody can tell which pieces carry the message.

> This project is fully vibe coded.

## Recommended: Web App (`index.html`)

**The web app is the best way to use ChessCipher.** Just open `index.html` in any browser — no server, no dependencies, no setup. It has a much better visual experience than the Python script, with drag-and-drop pieces, keyboard typing, animated transitions, and multiple modes including 1v1 encrypted messaging.

## How It Works

1. **You type a message** like `HELLO WORLD`
2. **Each character maps to a unique chess square** using a SHA-256 scrambled mapping (not sequential — you need the cipher seed to decode it)
3. **A realistic chess board is generated** with your message pieces + fake decoy pieces + both kings — looks like a real mid-game position
4. **The filename IS the cipher** — it's formatted as chess moves: `1.Be2+_e5_2.Rxh8_Rh8_3.Bxa5_Be6.png`
5. **To decrypt**, just copy the filename and paste it into the script — it extracts the squares from the move notation and maps them back to characters

The board image is never read during decryption. It's pure camouflage.

## What Makes It Convincing

- Both white and black pieces, always both kings present
- Realistic piece counts (max 2 rooks, 2 bishops, 2 knights per side)
- Pawns never on impossible ranks (1st or 8th)
- "Last move" highlight that follows actual chess movement rules (queens don't jump over pieces, knights move in L-shapes, etc.)
- Filename looks like standard PGN game notation with move numbers, captures (`x`), and check symbols (`+`)

## Web App (`index.html`)

Open `index.html` in any browser. No server needed.

### Modes

- **Encrypt** — type a message, see the board populate with pieces, get the filename
- **Decrypt** — paste a filename, see the decoded message
- **Free Board** — type a message with your keyboard and pieces auto-place on the board. Each character appears as a deletable chip, making it much easier than dragging pieces one by one. You can also still drag pieces from the tray.
- **1v1 Local Mode** — two-player encrypted messaging using chess pieces only. Players take turns composing and sending messages as chess board positions. The receiver sees only the pieces on the board — no plaintext. Toggle the letter overlay to decode the hidden message. All communication happens through piece placement.
- **Piece-Name Cipher** — an alternative encoding that uses chess piece initials (K=King, Q=Queen, R=Rook, B=Bishop, N=Knight, P=Pawn). Each character maps to a 2-letter piece code (e.g., `HELLO` = `QK.KN.QN.QN.RK`). The display shows actual piece icons instead of text, so you see the message as a sequence of chess pieces.

### Features

- Drag and drop pieces (pointer events, works on mobile)
- **Keyboard typing** in Free Board — just type and pieces appear
- **Message editor strip** below the board showing each character with its mapped square and piece — click any character to delete it
- **Smooth animations** — piece placement animations, transitions, and toast notifications
- Toggle letter overlay to see which character each square maps to
- Export board as PNG
- Copy filename with one click
- Staunton SVG chess pieces
- Dark theme (chess.com style)
- Responsive layout

## Python Script (`main.py`)

Command-line tool that generates board images. Functional but the web app is recommended for a better experience.

```
python main.py
```

Pick `1` to encrypt or `2` to decrypt.

**Encrypt:** type your message, get a PNG board image with the filename encoding the cipher.

**Decrypt:** paste the filename (without `.png`), get the original message back.

**Requirements:**
```
pip install pygame
```

## Supported Characters

```
A B C D E F G H I J K L M N O P Q R S T U V W X Y Z [space] 0 1 2 3 4 5 6 7 8 9
```

37 characters total. Messages are automatically converted to uppercase.

## File Structure

```
ChessCipher/
  main.py          # Python encryption/decryption script
  index.html       # Interactive web app (self-contained, recommended)
  report.html      # Detailed technical documentation
  pieces_svg.js    # SVG piece definitions
  color/           # 16x16 pixel art piece assets (used by main.py)
  README.md
```

## Security

This is a **steganography/obfuscation** tool, not a military-grade cipher. It's designed to hide messages from casual observers, not to resist cryptanalysis.

**What it does well:**
- Board looks like a normal chess game screenshot
- Filename looks like normal chess notation
- Scrambled mapping means you need the cipher seed to decode
- Same message always produces the same board (reproducible)

**Known limitations:**
- Cipher seed is hardcoded — anyone with the source code can decrypt
- Repeated characters map to the same square, so frequency analysis is possible on long messages
- Max ~50 character messages (limited by filename length)

For stronger security, change the `CIPHER_SEED` to a shared secret between sender and receiver.

## Quick Example

**Encrypt** `HELLO`:

```
Squares: e2 → H, e5 → E, h8 → L, h8 → L, a5 → O
Filename: 1.Be2+_e5_2.Rxh8_Rh8_3.a5.png
```

**Decrypt** — paste `1.Be2+_e5_2.Rxh8_Rh8_3.a5`:

```
Parser: Be2+ → e2, e5 → e5, Rxh8 → h8, Rh8 → h8, a5 → a5
Result: HELLO
```

## License

Do whatever you want with it.
