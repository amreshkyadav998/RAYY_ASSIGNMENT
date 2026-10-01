import { useEffect, useRef, useState } from "react";
import { formatPaise } from "./formatPaise";
import type { Order } from "./types";

/**
 * Shows the subtotal, the discount (code and amount) when there is one, and
 * the total, all through formatPaise, plus a "Pay" button that calls onPay.
 *
 * - The button is disabled while onPay is pending (no double submit); it
 *   still reads "Pay".
 * - Only when order.status is "paid" does the button read "Paid"; it is then
 *   disabled.
 * - If onPay rejects, show an error in an element with role="alert" and
 *   re-enable the button.
 */
export function OrderSummary(props: { order: Order; onPay: () => Promise<void> }): JSX.Element {
  const { order, onPay } = props;
  const [paying, setPaying] = useState(false);
  const [failed, setFailed] = useState(false);
  // A ref closes the gap between a click and the re-render that disables the button.
  const inFlight = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const paid = order.status === "paid";

  async function handlePay() {
    if (inFlight.current || paid) return;
    inFlight.current = true;
    setFailed(false);
    setPaying(true);
    try {
      await onPay();
    } catch {
      if (mounted.current) setFailed(true);
    } finally {
      inFlight.current = false;
      if (mounted.current) setPaying(false);
    }
  }

  return (
    <section aria-label="Order summary">
      <h2>Order {order.order_id}</h2>
      <dl>
        <div>
          <dt>Subtotal</dt>
          <dd>{formatPaise(order.subtotal_paise)}</dd>
        </div>
        {order.discount && (
          <div>
            <dt>
              Discount (<span data-testid="discount-code">{order.discount.code}</span>)
            </dt>
            <dd>
              <span aria-hidden="true">-</span>
              <span data-testid="discount-amount">{formatPaise(order.discount.amount_paise)}</span>
            </dd>
          </div>
        )}
        <div>
          <dt>Total</dt>
          <dd>{formatPaise(order.total_paise)}</dd>
        </div>
      </dl>
      {failed && <p role="alert">Payment failed. Please try again.</p>}
      <button type="button" onClick={handlePay} disabled={paid || paying} aria-busy={paying}>
        {paid ? "Paid" : "Pay"}
      </button>
    </section>
  );
}
