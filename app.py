import psycopg2
from flask import Flask, flash, request, jsonify
from con import set_connection
from loggerinstance import logger
import json

app = Flask(__name__)


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            conn = kwargs.get('conn')
            if conn:
                conn.rollback()
            logger.error(str(e))
            return jsonify({"error": "Database error"})
        except Exception as e:
            logger.error(str(e))
            return jsonify({"error": "Internal server error"})
        finally:
            conn = kwargs.get('conn')
            cur = kwargs.get('cur')
            if cur:
                cur.close()
            if conn:
                conn.close()
    return wrapper



cart = {}


@app.route('/v1/insert', methods=['POST'])
@handle_exceptions
def add_to_cart():
    # {
    #     "item": "string",
    #     "price": float,
    #     "quantity": int
    # }
    data = request.get_json()
    item = data.get('item')
    price = data.get('price')
    quantity = data.get('quantity')
    if not item or not price or not quantity:
        return jsonify({'error': 'Invalid payload.'}), 400

    cur, conn = set_connection()
    cur.execute(
        "INSERT INTO cart (item, price, quantity) VALUES (%s, %s, %s)",
        (item, price, quantity)
    )
    conn.commit()
    logger.info(f'Item {item} added to cart with price {price} and quantity {quantity}')

    if item in cart:
        cart[item]['quantity'] += quantity
        cart[item]['price'] += price
    else:
        cart[item] = {'quantity': quantity, 'price': price}
    added_item = {item: {'quantity': quantity, 'price': price}}
    return jsonify(added_item)


@app.route('/v1/get_cart', methods=['GET'], endpoint='get_cart')
@handle_exceptions
def get_cart():
    cur, conn = set_connection()

    cur.execute("SELECT item, price, quantity FROM cart")
    rows = cur.fetchall()

    temp_cart = {}
    for row in rows:
        item = row[0]
        price = row[1]
        quantity = row[2]
        if item in temp_cart:
            temp_cart[item]['quantity'] += quantity
            temp_cart[item]['price'] += price
        else:
            temp_cart[item] = {'quantity': quantity, 'price': price}
    logger.info(f"fetched from cart{temp_cart}")

    return jsonify(temp_cart)


@app.route('/v1/remove', methods=['DELETE'], endpoint='remove_from_cart')
@handle_exceptions
def remove_from_cart():
    {
        "item": "string",
        "quantity": int
    }
    data = request.get_json()
    item = data.get('item')
    quantity = data.get('quantity')
    if not item or not quantity:
        return jsonify({'error': 'Invalid payload.'}), 400
    cur, conn = set_connection()
    cur.execute(
        "UPDATE cart SET quantity = quantity - %s WHERE item = %s AND quantity >= %s",
        (quantity, item, quantity)
    )
    conn.commit()  # Commit the changes to the database
    logger.info(f'{quantity} {item} deleted from cart')

    if cur.rowcount == 0:
        return jsonify({'error': f'{item} not found in cart or not enough quantity.'}), 400

    # Update the cart dictionary
    if item in cart:
        cart_quantity = cart[item]['quantity']
        if cart_quantity <= quantity:
            del cart[item]
        else:
            cart[item]['quantity'] -= quantity

    cur.close()
    conn.close()
    message = f"{quantity} {item} deleted successfully."
    return jsonify({'message': message}), 200


@app.route('/v1/apply_discount', methods=['POST'], endpoint='apply_discount')
@handle_exceptions
def apply_discount():
    data = request.get_json()
    discount_percentage = data.get('discount')
    if not discount_percentage:
        return jsonify({'error': 'Invalid payload.'}), 400

    logger.info(f'Applying {discount_percentage}% discount')

    # Apply discount to cart items
    for item in cart:
        cart[item]['price'] *= (1 - (discount_percentage / 100))
    s = 0
    # for item in cart:
    #     s += cart[item]['price']

    return jsonify(
        {'message': f'{discount_percentage}% discount applied successfully.Total after applying discount is {s}'}), 200


@app.route('/v1/total', methods=['GET'], endpoint='get_total_cart')
@handle_exceptions
def get_total_cart():
    cur, conn = set_connection()
    cur.execute("SELECT SUM(price * quantity) FROM cart")
    total_price = cur.fetchone()[0]
    logger.info(f'Total cart price: {total_price}')

    return jsonify({'total_price': total_price})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
