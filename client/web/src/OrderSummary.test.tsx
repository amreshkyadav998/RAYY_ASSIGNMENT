import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OrderSummary } from "./OrderSummary";
import type { Order } from "./types";

const order: Order = {
  order_id: "ord_test_1",
  subtotal_paise: 19999,
  total_paise: 19999,
  status: "pending",
  discount: null,
};

const discounted: Order = {
  ...order,
  subtotal_paise: 199999,
  total_paise: 169999,
  discount: { code: "DEMO15", amount_paise: 30000 },
};

function deferred() {
  let resolve!: () => void;
  let reject!: (e: Error) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("OrderSummary", () => {
  it("renders", () => {
    render(<OrderSummary order={order} onPay={async () => {}} />);
    expect(screen.getByRole("region", { name: "Order summary" })).toBeInTheDocument();
  });

  it("shows subtotal and total through formatPaise, and no discount row when there is none", () => {
    render(<OrderSummary order={{ ...order, subtotal_paise: 199999, total_paise: 199999 }} onPay={async () => {}} />);
    expect(screen.getAllByText("₹1,999.99")).toHaveLength(2);
    expect(screen.queryByText(/discount/i)).not.toBeInTheDocument();
  });

  it("shows the discount code and amount, subtotal and total", () => {
    render(<OrderSummary order={discounted} onPay={async () => {}} />);
    expect(screen.getByText("₹1,999.99")).toBeInTheDocument();
    expect(screen.getByText("DEMO15")).toBeInTheDocument();
    expect(screen.getByText("₹300.00")).toBeInTheDocument();
    expect(screen.getByText("₹1,699.99")).toBeInTheDocument();
  });

  it("has an enabled Pay button that calls onPay", async () => {
    const onPay = vi.fn().mockResolvedValue(undefined);
    render(<OrderSummary order={order} onPay={onPay} />);
    const button = screen.getByRole("button", { name: "Pay" });
    expect(button).toBeEnabled();
    await userEvent.click(button);
    expect(onPay).toHaveBeenCalledTimes(1);
  });

  it("disables the button, still labelled Pay, while payment is in progress, and ignores extra clicks", async () => {
    const d = deferred();
    const onPay = vi.fn(() => d.promise);
    render(<OrderSummary order={order} onPay={onPay} />);
    const button = screen.getByRole("button", { name: "Pay" });
    await userEvent.click(button);
    expect(screen.getByRole("button", { name: "Pay" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Pay" }));
    expect(onPay).toHaveBeenCalledTimes(1);
    d.resolve();
    await waitFor(() => expect(screen.getByRole("button", { name: "Pay" })).toBeEnabled());
  });

  it("reads Paid and stays disabled only when the status is paid", async () => {
    const onPay = vi.fn();
    const { rerender } = render(<OrderSummary order={order} onPay={onPay} />);
    expect(screen.queryByRole("button", { name: "Paid" })).not.toBeInTheDocument();
    rerender(<OrderSummary order={{ ...order, status: "paid" }} onPay={onPay} />);
    const button = screen.getByRole("button", { name: "Paid" });
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(onPay).not.toHaveBeenCalled();
  });

  it("does not read Paid just because onPay resolved", async () => {
    render(<OrderSummary order={order} onPay={async () => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Pay" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Pay" })).toBeEnabled());
    expect(screen.queryByRole("button", { name: "Paid" })).not.toBeInTheDocument();
  });

  it("shows an alert when payment fails, re-enables the button, and allows a retry", async () => {
    const onPay = vi.fn().mockRejectedValueOnce(new Error("card declined")).mockResolvedValueOnce(undefined);
    render(<OrderSummary order={order} onPay={onPay} />);
    await userEvent.click(screen.getByRole("button", { name: "Pay" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/payment failed/i);
    const button = screen.getByRole("button", { name: "Pay" });
    expect(button).toBeEnabled();
    await userEvent.click(button);
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(onPay).toHaveBeenCalledTimes(2);
  });

  it("clears the error while a retry is in progress", async () => {
    const d = deferred();
    const onPay = vi.fn().mockRejectedValueOnce(new Error("x")).mockReturnValueOnce(d.promise);
    render(<OrderSummary order={order} onPay={onPay} />);
    await userEvent.click(screen.getByRole("button", { name: "Pay" }));
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: "Pay" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    d.resolve();
    await waitFor(() => expect(screen.getByRole("button", { name: "Pay" })).toBeEnabled());
  });
});
