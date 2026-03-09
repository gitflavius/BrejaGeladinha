import os
import time
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "girobeer-dev-secret")
database_url = os.getenv("DATABASE_URL", "sqlite:///girobeer.db")
# Railway uses postgres:// but SQLAlchemy requires postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# ─── Models ────────────────────────────────────────────────────────────────────

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default='')
    volume_ml = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, default=0)
    tag = db.Column(db.String(50), default='')
    image = db.Column(db.String(500), default='')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='Novo')
    total = db.Column(db.Float, default=0)
    created_at = db.Column(db.String(20))
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)


class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), default='')
    status = db.Column(db.String(50), default='Ativa')


# ─── Seed ──────────────────────────────────────────────────────────────────────

def _seed():
    if Branch.query.count() == 0:
        db.session.add_all([
            Branch(name="Giro Beer Matriz", city="Cuiabá/MT", status="Ativa"),
            Branch(name="Giro Beer CPA", city="Cuiabá/MT", status="Expansão"),
        ])
        db.session.flush()

    if Product.query.count() == 0:
        b1 = Branch.query.first()
        b2 = Branch.query.offset(1).first()
        db.session.add_all([
            Product(
                name="Heineken 600ml",
                category="Cervejas",
                volume_ml=600,
                price=11.90,
                stock=46,
                tag="premium",
                image="https://images.unsplash.com/photo-1608270586620-248524c67de9?auto=format&fit=crop&w=900&q=80",
                branch_id=b1.id if b1 else None
            ),
            Product(
                name="Combo Skol + Gelo",
                category="Combos",
                volume_ml=0,
                price=34.90,
                stock=4,
                tag="economia",
                image="https://images.unsplash.com/photo-1566633806327-68e152aaf26d?auto=format&fit=crop&w=900&q=80",
                branch_id=b1.id if b1 else None
            ),
            Product(
                name="Corona Long Neck",
                category="Cervejas",
                volume_ml=330,
                price=9.50,
                stock=31,
                tag="importada",
                image="https://images.unsplash.com/photo-1622483767028-3f66f32aef97?auto=format&fit=crop&w=900&q=80",
                branch_id=b2.id if b2 else None
            ),
            Product(
                name="Red Bull 250ml",
                category="Energeticos",
                volume_ml=250,
                price=12.90,
                stock=18,
                tag="energético",
                image="https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=900&q=80",
                branch_id=b2.id if b2 else None
            ),
        ])

    if Order.query.count() == 0:
        now = datetime.now().strftime("%d/%m %H:%M")
        db.session.add_all([
            Order(customer="Mateus", status="Novo", total=58.70, created_at=now),
            Order(customer="Ana", status="Preparando", total=27.80, created_at=now),
            Order(customer="Bruno", status="Saiu para entrega", total=42.90, created_at=now),
        ])

    db.session.commit()


with app.app_context():
    db.create_all()
    with db.engine.connect() as conn:
        for sql in [
            "ALTER TABLE product ADD COLUMN branch_id INTEGER REFERENCES branch(id)",
            "ALTER TABLE product ADD COLUMN volume_ml INTEGER DEFAULT 0",
            "ALTER TABLE \"order\" ADD COLUMN branch_id INTEGER REFERENCES branch(id)",
        ]:
            try:
                conn.execute(db.text(sql))
                conn.commit()
            except Exception:
                pass
    _seed()


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _save_image(file):
    if file and file.filename:
        ext = os.path.splitext(secure_filename(file.filename))[1].lower()
        if ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
            fname = f"prod_{int(time.time())}{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            return f"/static/uploads/{fname}"
    return None


def _require_admin():
    return not session.get("admin_logged_in")


def _admin_redirect():
    branch_id = request.args.get("branch_id") or request.form.get("branch_id_context")
    if branch_id:
        return redirect(url_for("admin", branch_id=branch_id))
    return redirect(url_for("admin"))


# ─── Init DB ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()


# ─── Public routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", products=Product.query.all())


@app.route("/app")
def app_view():
    return render_template(
        "app.html",
        products=Product.query.all(),
        branches=Branch.query.filter_by(status="Ativa").all()
    )


# ─── Admin auth ────────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        if (
            request.form.get("username") == ADMIN_USER and
            request.form.get("password") == ADMIN_PASSWORD
        ):
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        flash("Usuário ou senha inválidos.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# ─── Admin panel ───────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    if _require_admin():
        return redirect(url_for("admin_login"))

    branch_id = request.args.get("branch_id", type=int)

    branches = Branch.query.order_by(Branch.id.asc()).all()
    selected_branch = Branch.query.get(branch_id) if branch_id else None

    products_query = Product.query
    orders_query = Order.query

    if branch_id:
        products_query = products_query.filter(Product.branch_id == branch_id)
        orders_query = orders_query.filter(Order.branch_id == branch_id)

    products = products_query.all()
    orders = orders_query.order_by(Order.id.desc()).all()
    total_stock = sum(p.stock for p in products)

    return render_template(
        "admin.html",
        products=products,
        orders=orders,
        branches=branches,
        total_stock=total_stock,
        selected_branch=selected_branch,
        selected_branch_id=branch_id
    )


# ─── Products CRUD ─────────────────────────────────────────────────────────────

@app.route("/admin/products/add", methods=["POST"])
def admin_products_add():
    if _require_admin():
        return redirect(url_for("admin_login"))

    bid = request.form.get("branch_id")
    volume_ml = request.form.get("volume_ml")

    p = Product(
        name=request.form.get("name", ""),
        category=request.form.get("category", ""),
        volume_ml=int(volume_ml) if volume_ml else 0,
        price=float(request.form.get("price", 0)),
        stock=int(request.form.get("stock", 0)),
        tag=request.form.get("tag", ""),
        image=_save_image(request.files.get("image")) or "",
        branch_id=int(bid) if bid else None,
    )
    db.session.add(p)
    db.session.commit()
    return _admin_redirect()


@app.route("/admin/products/<int:product_id>/edit", methods=["POST"])
def admin_products_edit(product_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    p = Product.query.get_or_404(product_id)
    new_img = _save_image(request.files.get("image"))

    if new_img:
        p.image = new_img

    p.name = request.form.get("name", p.name)
    p.category = request.form.get("category", p.category)

    volume_ml = request.form.get("volume_ml")
    p.volume_ml = int(volume_ml) if volume_ml else 0

    p.price = float(request.form.get("price", p.price))
    p.stock = int(request.form.get("stock", p.stock))
    p.tag = request.form.get("tag", p.tag)

    bid = request.form.get("branch_id")
    p.branch_id = int(bid) if bid else None

    db.session.commit()
    return _admin_redirect()


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
def admin_products_delete(product_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    db.session.delete(Product.query.get_or_404(product_id))
    db.session.commit()
    return _admin_redirect()


@app.route("/admin/products/<int:product_id>/stock", methods=["POST"])
def admin_products_stock(product_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    p = Product.query.get_or_404(product_id)
    p.stock = int(request.form.get("quantity", p.stock))
    db.session.commit()
    return _admin_redirect()


# ─── Orders CRUD ───────────────────────────────────────────────────────────────

@app.route("/admin/orders/add", methods=["POST"])
def admin_orders_add():
    if _require_admin():
        return redirect(url_for("admin_login"))

    names = request.form.getlist("item_name[]")
    qtys = request.form.getlist("item_qty[]")
    prices = request.form.getlist("item_price[]")

    items = []
    total = 0.0

    for name, qty, price in zip(names, qtys, prices):
        if name.strip():
            q = int(qty or 1)
            pr = float(price or 0)
            items.append(OrderItem(product_name=name, quantity=q, unit_price=pr))
            total += q * pr

    branch_id_context = request.form.get("branch_id_context")

    order = Order(
        customer=request.form.get("customer", "Cliente"),
        status="Novo",
        total=round(total, 2),
        created_at=datetime.now().strftime("%d/%m %H:%M"),
        branch_id=int(branch_id_context) if branch_id_context else None,
        items=items,
    )

    db.session.add(order)
    db.session.commit()
    return _admin_redirect()


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
def admin_orders_status(order_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    o = Order.query.get_or_404(order_id)
    o.status = request.form.get("status", o.status)
    db.session.commit()
    return _admin_redirect()


@app.route("/admin/orders/<int:order_id>/delete", methods=["POST"])
def admin_orders_delete(order_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    db.session.delete(Order.query.get_or_404(order_id))
    db.session.commit()
    return _admin_redirect()


# ─── Branches CRUD ─────────────────────────────────────────────────────────────

@app.route("/admin/branches/add", methods=["POST"])
def admin_branches_add():
    if _require_admin():
        return redirect(url_for("admin_login"))

    b = Branch(
        name=request.form.get("name", ""),
        city=request.form.get("city", ""),
        status=request.form.get("status", "Ativa"),
    )
    db.session.add(b)
    db.session.commit()
    return _admin_redirect()


@app.route("/admin/branches/<int:branch_id>/edit", methods=["POST"])
def admin_branches_edit(branch_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    b = Branch.query.get_or_404(branch_id)
    b.name = request.form.get("name", b.name)
    b.city = request.form.get("city", b.city)
    b.status = request.form.get("status", b.status)
    db.session.commit()
    return _admin_redirect()


@app.route("/admin/branches/<int:branch_id>/delete", methods=["POST"])
def admin_branches_delete(branch_id):
    if _require_admin():
        return redirect(url_for("admin_login"))

    db.session.delete(Branch.query.get_or_404(branch_id))
    db.session.commit()
    return _admin_redirect()


# ─── Public API ────────────────────────────────────────────────────────────────

@app.route("/api/products")
def api_products():
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "volume_ml": p.volume_ml,
        "price": p.price,
        "stock": p.stock,
        "tag": p.tag,
        "image": p.image
    } for p in Product.query.all()])


@app.route("/api/orders", methods=["GET"])
def api_orders():
    return jsonify([{
        "id": o.id,
        "customer": o.customer,
        "status": o.status,
        "total": o.total
    } for o in Order.query.all()])


@app.route("/api/orders", methods=["POST"])
def api_orders_create():
    payload = request.get_json(silent=True) or {}
    customer = payload.get("customer", "Cliente")
    items = payload.get("items", [])
    total = round(sum(i.get("qty", 1) * i.get("price", 0) for i in items), 2)

    order = Order(
        customer=customer,
        status="Novo",
        total=total,
        created_at=datetime.now().strftime("%d/%m %H:%M"),
        branch_id=payload.get("branch_id") or None,
        items=[
            OrderItem(
                product_name=i.get("name", ""),
                quantity=i.get("qty", 1),
                unit_price=i.get("price", 0)
            )
            for i in items if i.get("name")
        ],
    )

    db.session.add(order)
    db.session.commit()
    return jsonify({"order_id": order.id, "total": total, "status": "Novo"})


@app.route("/api/branches")
def api_branches():
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "city": b.city,
        "status": b.status
    } for b in Branch.query.all()])


@app.route("/api/pix-preview", methods=["POST"])
def api_pix_preview():
    payload = request.get_json(silent=True) or {}
    total = float(payload.get("total", 0))
    order_id = int(payload.get("order_id", 0))
    return jsonify({
        "order_id": order_id,
        "total": total,
        "pix_code": f"00020126450014BR.GOV.BCB.PIX0114+55839999999995204000053039865405{total:.2f}5802BR5920GIRO BEER EMPORIO6009SAO PAULO62070503***6304ABCD"
    })




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)