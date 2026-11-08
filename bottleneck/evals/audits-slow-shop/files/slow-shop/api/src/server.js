const express = require('express');
const axios = require('axios');
const db = require('./db');

const app = express();
app.use(express.json());

// Orders screen: list the customer's orders with their items and totals.
app.get('/api/orders', async (req, res) => {
  const customerId = req.query.customer_id;
  const orders = await db('orders').select('*').where({ customer_id: customerId }).orderBy('created_at', 'desc');

  for (const order of orders) {
    order.items = await db('order_items').select('*').where({ order_id: order.id });
    order.total = order.items.reduce((sum, i) => sum + i.price * i.quantity, 0);
  }

  res.json(orders);
});

// Product catalog, same for every customer, changes once a week.
app.get('/api/products', async (req, res) => {
  const products = await db('products').select('*');
  res.json(products);
});

// Shipping quote from a third-party carrier.
app.post('/api/shipping-quote', async (req, res) => {
  const quote = await axios.post('https://carrier.example.com/v1/quote', req.body);
  res.json(quote.data);
});

app.listen(3000);
