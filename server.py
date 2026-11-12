import http.server, sqlite3, urllib.parse, html, os

# 画面に表示するお知らせメッセージ
message = ""

def init_db():
    """データベースの準備（表と商品の自動作成）"""
    conn = sqlite3.connect("shop.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, image TEXT, price INTEGER, stock INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS cart (product_id INTEGER, quantity INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, items TEXT, total INTEGER)")
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO products VALUES (?,?,?,?,?)", [
            (1, "えんぴつ", "pencil.jpg", 100, 10), (2, "ノート", "notebook.jpg", 200, 5),
            (3, "消しゴム", "eraser.jpg", 80, 8), (4, "定規", "ruler.jpg", 150, 6), (5, "ハサミ", "scissors.jpg", 300, 4)
        ])
    conn.commit()
    conn.close()

class SimpleShopHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """画像の配信、またはトップページ画面（HTML）を作って返す"""
        global message

        # 1. 画像の配信（安全のため images フォルダ内のファイルのみ返す）
        if self.path.startswith("/images/"):
            if ".." in self.path:  # フォルダ外へのアクセスを禁止
                self.send_response(403); self.end_headers(); return
            fname = os.path.basename(urllib.parse.unquote(self.path[8:].split("?")[0]))
            fpath = os.path.join(os.path.dirname(__file__), "images", fname)
            if os.path.isfile(fpath):
                ctype = "image/jpeg" if fpath.endswith((".jpg", ".jpeg")) else "image/png"
                with open(fpath, "rb") as f: data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_response(404); self.end_headers(); return

        # 2. トップページ以外（server.py や shop.db 等）へのアクセスは隠す
        if self.path not in ("/", "") and not self.path.startswith("/?"):
            self.send_response(404); self.end_headers(); return

        # 3. データベースから商品・カート・注文履歴を取得
        conn = sqlite3.connect("shop.db")
        c = conn.cursor()
        c.execute("SELECT id, name, image, price, stock FROM products")
        products = c.fetchall()
        c.execute("SELECT p.id, p.name, c.quantity, p.price * c.quantity FROM cart c JOIN products p ON c.product_id = p.id")
        cart_items = c.fetchall()
        total_price = sum(item[3] for item in cart_items)
        c.execute("SELECT id, name, items, total FROM orders ORDER BY id DESC LIMIT 10")
        orders = c.fetchall()
        conn.close()

        # メッセージ表示（表示したら空に戻す）
        msg_html = f"<div class='msg'>{html.escape(message)}</div>" if message else ""
        message = ""

        # 商品カードの一覧（HTML）を作成（在庫0なら売り切れボタン）
        cards_html = ""
        for p in products:
            btn = "<button type='button' disabled>売り切れ</button>" if p[4] <= 0 else f"<form method='POST'><input type='hidden' name='action' value='add'><input type='hidden' name='product_id' value='{p[0]}'><button type='submit'>カートに入れる</button></form>"
            cards_html += f"<div class='card'><img src='/images/{p[2]}' alt='{html.escape(p[1])}'><h3>{html.escape(p[1])}</h3><div class='price'>{p[3]}円</div><div class='stock'>在庫: {p[4]}個</div>{btn}</div>"

        # カートと注文履歴の表を作成
        cart_rows = "".join(f"<tr><td>{html.escape(it[1])}</td><td>{it[2]}個</td><td>{it[3]}円</td><td><form method='POST'><input type='hidden' name='action' value='delete'><input type='hidden' name='product_id' value='{it[0]}'><button type='submit' class='del-btn'>削除</button></form></td></tr>" for it in cart_items)
        order_rows = "".join(f"<tr><td>{o[0]}</td><td>{html.escape(o[1])}</td><td>{html.escape(o[2])}</td><td>{o[3]}円</td></tr>" for o in orders)

        # 画面全体のHTMLとCSS
        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>文房具店 ペンシル＆ノート</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.5; padding-bottom: 40px; }}
header {{ background: #1e3a8a; color: white; padding: 14px 20px; font-size: 1.25em; font-weight: bold; margin-bottom: 20px; }}
.container {{ max-width: 800px; margin: auto; padding: 0 15px; }}
h2 {{ font-size: 1.15em; margin: 25px 0 10px; border-left: 4px solid #1e3a8a; padding-left: 8px; color: #1e3a8a; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }}
.card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
.card img {{ width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 6px; margin-bottom: 6px; }}
.card h3 {{ font-size: 0.95em; margin-bottom: 4px; }}
.price {{ color: #b91c1c; font-weight: bold; font-size: 1.05em; }}
.stock {{ font-size: 0.8em; color: #64748b; margin-bottom: 8px; }}
.cart-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 0.9em; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; }}
.total {{ font-size: 1.3em; color: #b91c1c; font-weight: bold; margin: 10px 0; }}
.msg {{ background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; padding: 10px 14px; border-radius: 6px; font-weight: bold; margin-bottom: 15px; }}
button {{ background: #1e3a8a; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }}
button:disabled {{ background: #94a3b8; cursor: not-allowed; }}
.del-btn {{ background: #ef4444; }}
input[type="text"] {{ padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 4px; }}
</style>
</head>
<body>
<header>文房具店 ペンシル＆ノート</header>
<div class="container">
{msg_html}
<h2>商品一覧</h2>
<div class="grid">{cards_html}</div>

<h2>現在のカート</h2>
<div class="cart-card">
<table><tr><th>商品</th><th>数量</th><th>小計</th><th>操作</th></tr>{cart_rows}</table>
<div class="total">合計金額: {total_price}円</div>
<form method="POST">
    <input type="hidden" name="action" value="order">
    お名前: <input type="text" name="name" required placeholder="例: 山田 太郎">
    <button type="submit">注文する</button>
</form>
</div>

<h2>注文履歴</h2>
<div class="cart-card">
<table><tr><th>番号</th><th>お名前</th><th>商品</th><th>合計</th></tr>{order_rows}</table>
</div>
</div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_body.encode("utf-8"))

    def do_POST(self):
        """ボタンが押されたときの処理（カート追加・削除・注文）"""
        global message
        length = int(self.headers.get("Content-Length", 0))
        params = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        action = params.get("action", [""])[0]

        conn = sqlite3.connect("shop.db")
        c = conn.cursor()

        # 1. カートに入れる
        if action == "add":
            pid = int(params.get("product_id", [0])[0])
            c.execute("SELECT stock FROM products WHERE id = ?", (pid,))
            stock = c.fetchone()[0]
            c.execute("SELECT quantity FROM cart WHERE product_id = ?", (pid,))
            row = c.fetchone()
            qty = row[0] if row else 0

            if qty + 1 > stock:
                message = "在庫が足りません"
            elif row:
                c.execute("UPDATE cart SET quantity = quantity + 1 WHERE product_id = ?", (pid,))
            else:
                c.execute("INSERT INTO cart VALUES (?, 1)", (pid,))

        # 2. カートから削除
        elif action == "delete":
            pid = int(params.get("product_id", [0])[0])
            c.execute("DELETE FROM cart WHERE product_id = ?", (pid,))

        # 3. 注文する
        elif action == "order":
            name = params.get("name", [""])[0].strip()
            c.execute("SELECT p.id, p.name, c.quantity, p.stock, p.price FROM cart c JOIN products p ON c.product_id = p.id")
            items = c.fetchall()

            if not items:
                message = "カートが空です"
            elif any(it[2] > it[3] for it in items):
                message = "在庫が足りません"
            else:
                item_texts = []
                total = 0
                for pid, pname, qty, stock, price in items:
                    c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))
                    item_texts.append(f"{pname}×{qty}")
                    total += price * qty
                c.execute("INSERT INTO orders (name, items, total) VALUES (?, ?, ?)", (name, ", ".join(item_texts), total))
                order_id = c.lastrowid
                c.execute("DELETE FROM cart")
                message = f"注文番号 {order_id} で受け付けました"

        conn.commit()
        conn.close()

        # 処理が終わったらトップページへリダイレクト
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

if __name__ == "__main__":
    init_db()
    # 接続ごとに別々に処理する（1つの接続で止まらないように）
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 80), SimpleShopHandler)
    print("サーバーを起動しました: http://0.0.0.0:80")
    server.serve_forever()
