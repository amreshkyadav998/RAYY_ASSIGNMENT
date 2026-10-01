import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { OrderSummary } from "./OrderSummary";
import type { Order } from "./types";

// Local demo harness. URL options:
//   ?order=ord_a_1001   load that order from the API (proxied at /api, see vite.config.ts)
//   ?fail=1             make the Pay button fail (to see the error + retry)
//   ?status=paid        show the sample order as already paid
const params = new URLSearchParams(window.location.search);

const sample: Order = {
  order_id: "ord_demo_1",
  subtotal_paise: 199999,
  total_paise: 169999,
  status: params.get("status") ?? "pending",
  discount: { code: "DEMO15", amount_paise: 30000 },
};

async function loadOrder(id: string): Promise<Order> {
  const res = await fetch(`/api/orders/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`GET /orders/${id} -> ${res.status}`);
  const o = await res.json();
  return {
    order_id: o.order_id,
    subtotal_paise: o.subtotal_paise,
    total_paise: o.total_paise,
    status: o.status,
    discount: o.discount ? { code: o.discount.code, amount_paise: o.discount.amount_paise } : null,
  };
}

// Stand-in for "start a payment": the real flow is the gateway calling the webhook.
const onPay = () =>
  new Promise<void>((resolve, reject) =>
    setTimeout(() => (params.get("fail") ? reject(new Error("declined")) : resolve()), 1000),
  );

function App() {
  const orderId = params.get("order");
  const [order, setOrder] = useState<Order | null>(orderId ? null : sample);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (orderId) loadOrder(orderId).then(setOrder, (e) => setError(String(e.message)));
  }, [orderId]);
  if (error) return <p>{error}</p>;
  if (!order) return <p>Loading…</p>;
  return <OrderSummary order={order} onPay={onPay} />;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
