from flask import Blueprint, render_template, request, redirect, session
from ..models.database import get_db
import pandas as pd
import os
from recommendation_engines.hybrid_model import recommend_for_user, recommend_similar_products, recommend_accessories, recommend_same_price
import json
from math import ceil

# Load products
data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
products = pd.read_csv(os.path.join(data_dir, 'products.csv'))
ratings = pd.read_csv(os.path.join(data_dir, 'ratings.csv'))
main_bp = Blueprint('main', __name__)

@main_bp.route("/home")
def home():
    if "user" not in session:
        return redirect("/")

    username = session["user"]
    cart_count = len(session.get("cart", []))

    # Personalized recommendations
    recommended = recommend_for_user(username)

    # Show ALL products
    all_products = products.to_dict("records")

    return render_template(
        "home.html",
        products=all_products,
        recommended=recommended.to_dict("records"),
        username=username,
        cart_count=cart_count,
        product_count=len(products)
    )
  
@main_bp.route("/search")
def search():
    # basic GET-based search over name/category
    if "user" not in session:
        return redirect("/")
    query = request.args.get("q", "").strip()
    results = []
    if query:
        mask = (
            products['name'].str.contains(query, case=False, na=False) |
            products['category'].str.contains(query, case=False, na=False)
        )
        results = products[mask].to_dict('records')
    cart_count = len(session.get("cart", []))
    return render_template(
        "search.html",
        query=query,
        results=results,
        count=len(results),
        username=session.get("user"),
        cart_count=cart_count
    )

@main_bp.route("/view/<int:product_id>")
def view_product(product_id):
    if "user" not in session:
        return redirect("/")

    username = session["user"]

    # Get product
    product = products[products['product_id'] == product_id].to_dict('records')[0]

    # Get average rating from ratings.csv
    product_ratings = ratings[ratings['product_id'] == product_id]

    if not product_ratings.empty:
        avg_rating = round(product_ratings['rating'].mean(), 1)
    else:
        avg_rating = "N/A"

    # Add extra fields for UI
    product["rating"] = avg_rating
    product["color"] = "Standard"
    product["description"] = "Premium quality product available in our store."

    # Save interaction
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO interactions (username, product_id) VALUES (?, ?)",
            (username, product_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("warning: unable to save view interaction", e)

    # Get recommendations
    similar = recommend_similar_products(product_id)
    accessories = recommend_accessories(product_id)
    same_price = recommend_same_price(product_id)

    return render_template(
        "recommend.html",
        product=product,
        similar=similar.to_dict("records"),
        accessories=accessories.to_dict("records"),
        same_price=same_price.to_dict("records"),
        username=username
    )

@main_bp.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "user" not in session:
        return redirect("/")

    if "cart" not in session:
        session["cart"] = []

    session["cart"].append(product_id)
    session.modified = True

    # Record interaction (non‑critical; don't crash the app if the
    # table schema is wrong or the write fails).  The tests above have
    # already shown that the session cart works independently of the
    # database, and a failure here shouldn't prevent the user from
    # continuing to shop.
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO interactions (username, product_id, interaction_type) VALUES (?, ?, ?)",
            (session["user"], product_id, "add_to_cart")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # log to stderr; Flask will print this automatically
        print("warning: failed to record interaction", e)

    return redirect("/home")

@main_bp.route("/cart")
def cart():
    if "user" not in session:
        return redirect("/")

    cart_items = []
    if "cart" in session:
        for pid in session["cart"]:
            product = products[products['product_id'] == pid].to_dict('records')[0]
            cart_items.append(product)

    return render_template("cart.html", cart=cart_items)

@main_bp.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    if "user" not in session:
        return redirect("/")

    if "cart" in session and product_id in session["cart"]:
        session["cart"].remove(product_id)
        session.modified = True

    return redirect("/cart")

@main_bp.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/")

    cart_items = []
    if "cart" in session:
        for pid in session["cart"]:
            product = products[products['product_id'] == pid].to_dict('records')[0]
            cart_items.append(product)

    total = sum([p.get('price', 0) for p in cart_items])

    # load saved addresses for the user
    username = session['user']
    addresses = []
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT id, label, address_line1, address_line2, city, state, postal_code, country FROM addresses WHERE username=? ORDER BY is_default DESC, created_at DESC",
            (username,)
        ).fetchall()
        conn.close()
        for r in rows:
            addresses.append({
                'id': r['id'],
                'label': r['label'],
                'address_line1': r['address_line1'],
                'address_line2': r['address_line2'],
                'city': r['city'],
                'state': r['state'],
                'postal_code': r['postal_code'],
                'country': r['country']
            })
    except Exception as e:
        print('warning: failed to load addresses', e)

    return render_template("checkout.html", cart=cart_items, total=total, addresses=addresses)


@main_bp.route('/payment', methods=['POST', 'GET'])
def payment():
    if 'user' not in session:
        return redirect('/')

    # Expect POST from checkout with address fields or selected_address_id
    if request.method == 'GET':
        return redirect('/checkout')

    selected_address_id = request.form.get('selected_address_id')
    save_address = request.form.get('save_address')
    address_label = request.form.get('address_label', '')

    address = {
        'address_line1': request.form.get('address_line1', ''),
        'address_line2': request.form.get('address_line2', ''),
        'city': request.form.get('city', ''),
        'state': request.form.get('state', ''),
        'postal_code': request.form.get('postal_code', ''),
        'country': request.form.get('country', '')
    }

    # If selected_address_id provided, load it
    if selected_address_id:
        try:
            conn = get_db()
            row = conn.execute('SELECT address_line1,address_line2,city,state,postal_code,country FROM addresses WHERE id=? AND username=?', (selected_address_id, session['user'])).fetchone()
            conn.close()
            if row:
                address = {
                    'address_line1': row['address_line1'],
                    'address_line2': row['address_line2'],
                    'city': row['city'],
                    'state': row['state'],
                    'postal_code': row['postal_code'],
                    'country': row['country']
                }
        except Exception as e:
            print('warning: failed to load selected address for payment', e)

    # Build items from session cart
    cart = session.get('cart', [])
    items = []
    total = 0
    for pid in cart:
        p = products[products['product_id'] == pid].to_dict('records')[0]
        items.append(p)
        total += p.get('price', 0)

    return render_template('payment.html', items=items, total=total, address=address, selected_address_id=selected_address_id, save_address=save_address, address_label=address_label)

@main_bp.route("/place_order", methods=["POST"])
def place_order():
    if "user" not in session:
        return redirect("/")

    # If user selected a saved address, use it; otherwise read address fields from form
    selected_address_id = request.form.get('selected_address_id')

    address_line1 = request.form.get('address_line1', '')
    address_line2 = request.form.get('address_line2', '')
    city = request.form.get('city', '')
    state = request.form.get('state', '')
    postal_code = request.form.get('postal_code', '')
    country = request.form.get('country', '')

    if selected_address_id:
        try:
            conn = get_db()
            row = conn.execute(
                "SELECT address_line1, address_line2, city, state, postal_code, country FROM addresses WHERE id=? AND username=?",
                (selected_address_id, session['user'])
            ).fetchone()
            conn.close()
            if row:
                address_line1 = row['address_line1']
                address_line2 = row['address_line2']
                city = row['city']
                state = row['state']
                postal_code = row['postal_code']
                country = row['country']
        except Exception as e:
            print('warning: failed to load selected address', e)

    cart = session.get('cart', [])

    # build order items list
    items = []
    total = 0
    for pid in cart:
        product = products[products['product_id'] == pid].to_dict('records')[0]
        items.append(product)
        total += product.get('price', 0)

    # store order in database
    try:
        conn = get_db()
        cursor = conn.cursor()
        # read payment info (simulated)
        payment_method = request.form.get('payment_method', 'cod')
        card_number = request.form.get('card_number', '')
        upi_id = request.form.get('upi_id', '')

        # simulate payment processing
        if payment_method == 'card':
            payment_status = 'paid' if card_number and len(card_number) >= 12 else 'failed'
        elif payment_method == 'upi':
            payment_status = 'paid' if upi_id and '@' in upi_id else 'failed'
        else:
            payment_status = 'pending'

        cursor.execute(
            "INSERT INTO orders (username, items, total, address_line1, address_line2, city, state, postal_code, country, payment_method, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session['user'],
                json.dumps(items),
                total,
                address_line1,
                address_line2,
                city,
                state,
                postal_code,
                country,
                payment_method,
                payment_status
            )
        )
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()
    except Exception as e:
        print('warning: failed to save order', e)
        order_id = None

    # Optionally save address to user profile
    try:
        if not selected_address_id and request.form.get('save_address') == 'on':
            label = request.form.get('address_label', 'Saved Address')
            conn = get_db()
            conn.execute(
                "INSERT INTO addresses (username, label, address_line1, address_line2, city, state, postal_code, country) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session['user'], label, address_line1, address_line2, city, state, postal_code, country)
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print('warning: failed to save address', e)

    # Clear cart
    session['cart'] = []
    session.modified = True

    return render_template('order_success.html', order_id=order_id, items=items, total=total, address={
        'address_line1': address_line1,
        'address_line2': address_line2,
        'city': city,
        'state': state,
        'postal_code': postal_code,
        'country': country
    })


@main_bp.route('/orders')
def orders():
    if 'user' not in session:
        return redirect('/')

    username = session['user']
    orders = []
    try:
        conn = get_db()
        rows = conn.execute('SELECT id, items, total, address_line1, address_line2, city, state, postal_code, country, created_at FROM orders WHERE username=? ORDER BY created_at DESC', (username,)).fetchall()
        conn.close()
        for r in rows:
            items = []
            try:
                items = json.loads(r['items'])
            except Exception:
                items = []
            orders.append({
                'id': r['id'],
                'items': items,
                'total': r['total'],
                'address': {
                    'address_line1': r['address_line1'],
                    'address_line2': r['address_line2'],
                    'city': r['city'],
                    'state': r['state'],
                    'postal_code': r['postal_code'],
                    'country': r['country']
                },
                'created_at': r['created_at']
            })
    except Exception as e:
        print('warning: failed to load orders', e)

    return render_template('orders.html', orders=orders, username=username)