from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
import pymysql
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Reemplaza con una clave secreta segura

# Configuraciones
SECRET_NAME = "rds!db-3419db02-547f-45a3-b45e-690fb0626b69"
REGION_NAME = "us-east-1"
BUCKET_NAME = "ecommerce-store-images"
CARPETA_S3 = "products/"
RDS_HOST = "ecommerce-db.cdj5i4puctle.us-east-1.rds.amazonaws.com"
RDS_PORT = 3306

def get_secret():
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION_NAME)
    response = client.get_secret_value(SecretId=SECRET_NAME)
    return eval(response['SecretString'])

def get_db_connection(secret, use_db=True):
    return pymysql.connect(
        host=RDS_HOST,
        user=secret["username"],
        password=secret["password"],
        database="ecommerce_db" if use_db else None,
        port=RDS_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )

def create_database_if_not_exists(secret):
    connection = get_db_connection(secret, use_db=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS ecommerce_db;")
    finally:
        connection.close()

def create_table_if_not_exists(secret):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    description TEXT,
                    image_url VARCHAR(255) NOT NULL
                );
            """)
            connection.commit()
    finally:
        connection.close()

def upload_to_s3(file):
    s3 = boto3.client('s3')
    file_name = file.filename
    s3_key = os.path.join(CARPETA_S3, file_name)
    s3.upload_fileobj(file, BUCKET_NAME, s3_key)
    return f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{s3_key}"

def fetch_all_products(secret):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM products;")
            return cursor.fetchall()
    finally:
        connection.close()

def insert_product_to_db(secret, name, price, description, image_url):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO products (name, price, description, image_url)
                VALUES (%s, %s, %s, %s);
            """, (name, price, description, image_url))
            connection.commit()
    finally:
        connection.close()

def delete_product(secret, product_id):
    connection = get_db_connection(secret)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM products WHERE id = %s;", (product_id,))
            connection.commit()
    finally:
        connection.close()

# Inicialización
secret = get_secret()
create_database_if_not_exists(secret)
create_table_if_not_exists(secret)

# Rutas
@app.route('/')
def index():
    products = fetch_all_products(secret)
    return render_template('index.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            description = request.form['description']
            image = request.files['image']

            if not image:
                flash('La imagen es requerida.', 'danger')
                return redirect(request.url)

            image_url = upload_to_s3(image)
            insert_product_to_db(secret, name, price, description, image_url)
            flash(f"Producto '{name}' agregado exitosamente.", 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error al agregar el producto: {e}", 'danger')
            return redirect(request.url)
    return render_template('add_product.html')

@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product_route(product_id):
    try:
        delete_product(secret, product_id)
        flash(f"Producto con ID {product_id} eliminado exitosamente.", 'success')
    except Exception as e:
        flash(f"Error al eliminar el producto: {e}", 'danger')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)

