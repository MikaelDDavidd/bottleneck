import React, { useEffect, useState } from 'react';
import _ from 'lodash';

export default function Catalog() {
  const [products, setProducts] = useState([]);
  const [q, setQ] = useState('');
  useEffect(() => {
    fetch(`/api/products?q=${q}`).then((r) => r.json()).then(setProducts);
  }, [q]);
  return (
    <div>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" />
      {_.sortBy(products, 'name').map((p) => (
        <div key={p.id}>
          <img src={`data:image/jpeg;base64,${p.photo_base64}`} alt={p.name} />
          {p.name}
        </div>
      ))}
    </div>
  );
}
