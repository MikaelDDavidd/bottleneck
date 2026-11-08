import React, { useEffect, useState } from 'react';

export default function Orders() {
  const [orders, setOrders] = useState(null);
  useEffect(() => {
    fetch('/api/orders?customer_id=1').then((r) => r.json()).then(setOrders);
  }, []);
  if (!orders) return <div className="spinner">Loading...</div>;
  return (
    <ul>
      {orders.map((o) => (
        <li key={o.id}>#{o.id} - {o.items.length} items - {o.total}</li>
      ))}
    </ul>
  );
}
