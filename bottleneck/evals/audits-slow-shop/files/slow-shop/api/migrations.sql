CREATE TABLE customers (id serial PRIMARY KEY, name text NOT NULL);
CREATE TABLE products (id serial PRIMARY KEY, name text, description text, photo_base64 text, price numeric);
CREATE TABLE orders (id serial PRIMARY KEY, customer_id int REFERENCES customers(id), created_at timestamptz DEFAULT now(), notes text);
CREATE TABLE order_items (id serial PRIMARY KEY, order_id int REFERENCES orders(id), product_id int REFERENCES products(id), price numeric, quantity int);
