import os
import random
import hashlib
import re
import sys

try:
    import pygame  # only needed to render the PNG; the cipher itself is pure Python
except ImportError:  # pragma: no cover
    pygame = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIECE_DIR = os.path.join(SCRIPT_DIR, 'color')

SQ = 100
MARGIN = 30
BOARD_PX = SQ * 8
PIECE_SIZE = int(SQ * 0.82)

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
HL_LIGHT = (205, 210, 106)
HL_DARK = (170, 162, 58)
FRAME = (49, 46, 43)
LBL_ON_LIGHT = (186, 137, 96)
LBL_ON_DARK = (236, 218, 185)

CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789'
CIPHER_SEED = b'chess_cipher_v4'

PIECE_NOTATION = {
    'king': 'K', 'queen': 'Q', 'rook': 'R',
    'bishop': 'B', 'knight': 'N', 'pawn': ''
}

BACK_RANK = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']

PIECE_LIMITS = {
    'pawn': 8, 'rook': 2, 'knight': 2, 'bishop': 2, 'queen': 1, 'king': 1
}

_piece_cache = {}


def load_piece(color, piece):
    key = (color, piece)
    if key in _piece_cache:
        return _piece_cache[key]

    path = os.path.join(PIECE_DIR, f"{color}_{piece}.png")
    if not os.path.exists(path):
        _piece_cache[key] = None
        return None

    raw = pygame.image.load(path).convert_alpha()
    scaled = pygame.transform.smoothscale(raw, (PIECE_SIZE, PIECE_SIZE))
    _piece_cache[key] = scaled
    return scaled


ALL_SQUARES = [f"{f}{r}" for r in '12345678' for f in 'abcdefgh']

# Format v2: every square stands for a character. E, T, A and space get 3
# squares, Q, Z, X, J and the digits get 1, every other letter gets 2. The k-th
# occurrence of a character uses candidate k mod n, so repeated letters land on
# different squares. A v2 filename ends with a checksum move and a game result
# (1-0 / 0-1), which marks the format. index.html implements the same scheme.
V2_SLOTS = {'E': 3, 'T': 3, 'A': 3, ' ': 3, 'Q': 1, 'Z': 1, 'X': 1, 'J': 1}
RESULT_TOKENS = ('1-0', '0-1', '\u00bd-\u00bd')
NOT_CIPHER_MSG = "This doesn't look like a ChessCipher message."


def slot_count(ch):
    if ch in V2_SLOTS:
        return V2_SLOTS[ch]
    return 1 if ch.isdigit() else 2


def create_mapping():
    """v2 mapping: returns (char -> list of candidate squares, square -> char)."""
    squares = sorted(ALL_SQUARES,
                     key=lambda s: hashlib.sha256(CIPHER_SEED + b':v2:' + s.encode()).hexdigest())
    c2s, s2c, k = {}, {}, 0
    for ch in CHARACTERS:
        n = slot_count(ch)
        c2s[ch] = squares[k:k + n]
        for sq in c2s[ch]:
            s2c[sq] = ch
        k += n
    return c2s, s2c


def create_legacy_mapping():
    """v1 mapping (one square per character), kept so old filenames still decode."""
    squares = sorted(ALL_SQUARES, key=lambda s: hashlib.sha256(CIPHER_SEED + s.encode()).hexdigest())
    c2s = {ch: squares[i] for i, ch in enumerate(CHARACTERS)}
    s2c = {squares[i]: ch for i, ch in enumerate(CHARACTERS)}
    return c2s, s2c


def message_to_squares(msg, c2s=None):
    """Squares for a message, rotating through each character's candidates."""
    if c2s is None:
        c2s, _ = create_mapping()
    seen = {}
    out = []
    for ch in msg:
        cands = c2s[ch]
        k = seen.get(ch, 0)
        seen[ch] = k + 1
        out.append(cands[k % len(cands)])
    return out


def checksum_square(msg):
    n = int(hashlib.sha256(CIPHER_SEED + b':check:' + msg.encode()).hexdigest()[:8], 16) % 64
    return ALL_SQUARES[n]


def result_token(n_moves):
    return '1-0' if n_moves % 2 else '0-1'


def is_light_square(sq):
    col = ord(sq[0]) - ord('a')
    row = int(sq[1]) - 1
    return ((7 - row) + col) % 2 == 0


def sq_to_px(sq):
    col = ord(sq[0]) - ord('a')
    row = int(sq[1]) - 1
    return MARGIN + col * SQ, MARGIN + (7 - row) * SQ


def pick_piece_type(sq, rng):
    rank = int(sq[1])
    fi = ord(sq[0]) - ord('a')
    if rank in (1, 8):
        return BACK_RANK[fi]
    if rank in (2, 7):
        return 'pawn' if rng.random() < 0.75 else rng.choice(['knight', 'bishop'])
    return rng.choices(
        ['pawn', 'knight', 'bishop', 'rook', 'queen'],
        weights=[50, 15, 15, 12, 8]
    )[0]


def pick_color(sq, rng):
    rank = int(sq[1])
    if rank <= 2:
        return 'white' if rng.random() < 0.8 else 'black'
    if rank >= 7:
        return 'black' if rng.random() < 0.8 else 'white'
    return rng.choice(['white', 'black'])


def count_pieces(board):
    counts = {'white': {}, 'black': {}}
    for c, p in board.values():
        counts[c][p] = counts[c].get(p, 0) + 1
    return counts


def piece_allowed(counts, color, piece):
    current = counts.get(color, {}).get(piece, 0)
    return current < PIECE_LIMITS.get(piece, 99)


def pick_valid_piece(sq, color, counts, rng):
    pt = pick_piece_type(sq, rng)
    if pt == 'king':
        pt = 'pawn'
    if pt == 'pawn' and int(sq[1]) in (1, 8):
        pt = rng.choice(['knight', 'bishop', 'rook'])

    if piece_allowed(counts, color, pt):
        return pt

    fallbacks = ['pawn', 'knight', 'bishop', 'rook', 'queen']
    rng.shuffle(fallbacks)
    for fb in fallbacks:
        if fb == 'pawn' and int(sq[1]) in (1, 8):
            continue
        if piece_allowed(counts, color, fb):
            return fb
    return None


def get_legal_origins(sq, color, piece, board):
    col, row = ord(sq[0]) - ord('a'), int(sq[1]) - 1
    pts = []
    if piece == 'pawn':
        d = -1 if color == 'white' else 1
        if 0 <= row + d < 8:
            pts.append((col, row + d))
        if color == 'white' and row == 3:
            mid = f"{chr(ord('a') + col)}{row + 1}"
            if mid not in board:
                pts.append((col, row + 2))
        if color == 'black' and row == 4:
            mid = f"{chr(ord('a') + col)}{row}"
            if mid not in board:
                pts.append((col, row - 2))
        for dc in [-1, 1]:
            nc = col + dc
            if 0 <= nc < 8 and 0 <= row + d < 8:
                pts.append((nc, row + d))
    elif piece == 'knight':
        for dc, dr in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nc, nr = col + dc, row + dr
            if 0 <= nc < 8 and 0 <= nr < 8:
                pts.append((nc, nr))
    elif piece == 'king':
        for dc in [-1,0,1]:
            for dr in [-1,0,1]:
                if dc or dr:
                    nc, nr = col + dc, row + dr
                    if 0 <= nc < 8 and 0 <= nr < 8:
                        pts.append((nc, nr))
    else:
        dirs = []
        if piece in ('bishop', 'queen'):
            dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
        if piece in ('rook', 'queen'):
            dirs += [(-1,0),(1,0),(0,-1),(0,1)]
        for dc, dr in dirs:
            for dist in range(1, 8):
                nc, nr = col + dc * dist, row + dr * dist
                if not (0 <= nc < 8 and 0 <= nr < 8):
                    break
                csq = f"{chr(ord('a') + nc)}{nr + 1}"
                if csq in board:
                    break
                pts.append((nc, nr))
    return [f"{chr(ord('a') + c)}{r + 1}" for c, r in pts]


def make_notation(sq, piece, rng):
    pf = PIECE_NOTATION[piece]
    cap = 'x' if pf and rng.random() < 0.2 else ''
    chk = '+' if rng.random() < 0.06 else ''
    return f"{pf}{cap}{sq}{chk}"


def format_filename(moves, result=None):
    parts = []
    for i, m in enumerate(moves):
        parts.append(f"{i // 2 + 1}.{m}" if i % 2 == 0 else m)
    name = '_'.join(parts)
    if len(name) > 240:
        name = '_'.join(moves)
    if result:
        name += '_' + result
    return re.sub(r'[<>:"/\\|?*]', '', name) + '.png'


def parse_cipher(text):
    """Return (squares, is_v2) for a filename."""
    text = re.sub(r'\.png$', '', text.strip().strip('"').strip("'").strip(), flags=re.I)
    toks = [t.strip() for t in text.split('_') if t.strip()]
    v2 = False
    if toks and re.sub(r'^\d+\.', '', toks[-1]) in RESULT_TOKENS:
        v2 = True
        toks.pop()
    out = []
    for tok in toks:
        tok = re.sub(r'^\d+\.', '', tok).rstrip('+#')
        if len(tok) >= 2:
            sq = tok[-2:].lower()
            if sq[0] in 'abcdefgh' and sq[1] in '12345678':
                out.append(sq)
    return out, v2


def parse_filename(text):
    return parse_cipher(text)[0]


def decode_filename(text):
    """Decode a filename. Returns the message, or None if it isn't a ChessCipher message."""
    squares, v2 = parse_cipher(text)
    if not squares:
        return None
    if v2:
        if len(squares) < 2:
            return None
        _, s2c = create_mapping()
        msg = ''.join(s2c[s] for s in squares[:-1])
        return msg if checksum_square(msg) == squares[-1] else None
    _, s2c = create_legacy_mapping()
    if not all(s in s2c for s in squares):
        return None
    return ''.join(s2c[s] for s in squares)


def encode_squares(msg):
    """All board squares for a v2 message: the message squares plus the checksum square."""
    return message_to_squares(msg) + [checksum_square(msg)]


def generate_board(msg_squares, msg_text, result=None):
    seed = int(hashlib.sha256(msg_text.encode()).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)

    canvas_size = BOARD_PX + 2 * MARGIN
    surface = pygame.Surface((canvas_size, canvas_size))
    surface.fill(FRAME)

    board = {}
    msg_counts = {'white': {}, 'black': {}}

    for idx, sq in enumerate(msg_squares):
        if sq not in board:
            pc = 'white' if idx % 2 == 0 else 'black'
            pt = pick_piece_type(sq, rng)
            if pt == 'king':
                pt = rng.choice(['queen', 'rook', 'bishop', 'knight'])
            if not piece_allowed(msg_counts, pc, pt):
                pt = pick_valid_piece(sq, pc, msg_counts, rng)
                if pt is None:
                    pt = 'pawn'
            # A pawn can't arrive on its own back two ranks: use a minor piece instead
            rank = int(sq[1])
            if pt == 'pawn' and ((pc == 'white' and rank <= 2) or (pc == 'black' and rank >= 7)):
                pt = rng.choice(['knight', 'bishop'])
            board[sq] = (pc, pt)
            msg_counts[pc][pt] = msg_counts[pc].get(pt, 0) + 1

    all_sqs = [f"{f}{r}" for r in '12345678' for f in 'abcdefgh']
    free = [s for s in all_sqs if s not in board]

    for color, prefs, fallback_ranks in [
        ('white', ['g1', 'e1', 'f1', 'c1', 'h1'], '123'),
        ('black', ['g8', 'e8', 'f8', 'c8', 'h8'], '678'),
    ]:
        if not any(c == color and p == 'king' for c, p in board.values()):
            placed = False
            for cand in prefs:
                if cand in free:
                    board[cand] = (color, 'king')
                    free.remove(cand)
                    placed = True
                    break
            if not placed:
                fb = [s for s in free if s[1] in fallback_ranks]
                if fb:
                    sq = rng.choice(fb)
                    board[sq] = (color, 'king')
                    free.remove(sq)

    target = rng.randint(22, 30)
    need = max(0, target - len(board))
    rng.shuffle(free)
    wc = sum(1 for c, _ in board.values() if c == 'white')
    bc = len(board) - wc

    counts = count_pieces(board)

    for sq in free[:need]:
        if wc < bc - 2:
            pc = 'white'
        elif bc < wc - 2:
            pc = 'black'
        else:
            pc = pick_color(sq, rng)

        pt = pick_valid_piece(sq, pc, counts, rng)
        if pt is None:
            other = 'black' if pc == 'white' else 'white'
            pt = pick_valid_piece(sq, other, counts, rng)
            if pt is not None:
                pc = other
            else:
                continue

        board[sq] = (pc, pt)
        counts[pc][pt] = counts[pc].get(pt, 0) + 1
        if pc == 'white':
            wc += 1
        else:
            bc += 1

    occupied = list(board.keys())
    empty_after = [s for s in all_sqs if s not in board]
    hl_set = set()
    rng.shuffle(occupied)
    for to_sq in occupied:
        origins = get_legal_origins(to_sq, *board[to_sq], board)
        valid = [o for o in origins if o in empty_after]
        if valid:
            from_sq = rng.choice(valid)
            hl_set = {to_sq, from_sq}
            break

    for r in range(8):
        for c in range(8):
            sq_name = f"{chr(ord('a') + c)}{8 - r}"
            x, y = MARGIN + c * SQ, MARGIN + r * SQ
            light = (r + c) % 2 == 0
            if sq_name in hl_set:
                fill = HL_LIGHT if light else HL_DARK
            else:
                fill = LIGHT if light else DARK
            pygame.draw.rect(surface, fill, (x, y, SQ, SQ))

    try:
        lbl_font = pygame.font.SysFont('Arial', 14, bold=True)
    except:
        lbl_font = pygame.font.Font(None, 16)

    for i, f in enumerate('abcdefgh'):
        sq_name = f"{f}1"
        tc = LBL_ON_LIGHT if is_light_square(sq_name) else LBL_ON_DARK
        txt = lbl_font.render(f, True, tc)
        lx = MARGIN + i * SQ + SQ - txt.get_width() - 4
        ly = MARGIN + 7 * SQ + SQ - txt.get_height() - 3
        surface.blit(txt, (lx, ly))

    for i in range(8):
        sq_name = f"a{i + 1}"
        tc = LBL_ON_LIGHT if is_light_square(sq_name) else LBL_ON_DARK
        txt = lbl_font.render(str(i + 1), True, tc)
        lx = MARGIN + 4
        ly = MARGIN + (7 - i) * SQ + 3
        surface.blit(txt, (lx, ly))

    offset = (SQ - PIECE_SIZE) // 2
    for sq, (pc, pt) in board.items():
        piece_img = load_piece(pc, pt)
        if piece_img:
            px, py = sq_to_px(sq)
            surface.blit(piece_img, (px + offset, py + offset))

    moves = [make_notation(sq, board[sq][1], rng) for sq in msg_squares]
    fname = format_filename(moves, result)
    fpath = os.path.join(SCRIPT_DIR, fname)
    pygame.image.save(surface, fpath)

    print(f"\nBoard saved as: {fname}")
    print("To decrypt, copy the filename (without .png) and paste it in decrypt mode.")

    return fname


def encrypt():
    c2s, _ = create_mapping()
    msg = input("\nEnter message to encrypt: ").upper()
    if not msg:
        print("Empty message.")
        return
    bad = [c for c in msg if c not in c2s]
    if bad:
        print(f"Unsupported characters: {set(bad)}")
        print(f"Supported: {CHARACTERS}")
        return
    squares = encode_squares(msg)
    generate_board(squares, msg, result_token(len(squares)))


def decrypt():
    code = input("\nPaste the filename (without .png): ").strip().strip('"').strip("'")
    if not code:
        print("No input.")
        return
    if not parse_filename(code):
        print("No valid moves found in that input.")
        return
    result = decode_filename(code)
    if result is None:
        print(f"\n{NOT_CIPHER_MSG}")
        return
    print(f"\nDecrypted: {result}")


if __name__ == '__main__':
    if pygame is None:
        sys.exit("pygame is required to render boards: pip install pygame")
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    pygame.init()
    pygame.display.set_mode((1, 1))

    print("=" * 42)
    print("  CHESS CIPHER v5.0 (Steganographic)")
    print("=" * 42)
    print("1 : Encrypt (generate board image)")
    print("2 : Decrypt (from filename)")
    choice = input("\nPick: ").strip()
    if choice == '1':
        encrypt()
    elif choice == '2':
        decrypt()
    else:
        print("Invalid option")

    pygame.quit()
