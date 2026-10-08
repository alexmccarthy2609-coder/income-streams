// Invoice form: line items, live total and the saved-client picker.
// Used by the logged-in invoice form and the free no-signup generator.
// Adds a line-item row (description, quantity, price, remove button).
function addItem(description = "", quantity = 1, price = 0) {
  const row = document.createElement("div");
  row.className = "item";
  row.innerHTML = `
    <input name="description" placeholder="Description" required>
    <input name="quantity" type="number" min="0" step="any" aria-label="Quantity">
    <input name="unit_price" type="number" min="0" step="0.01" aria-label="Unit price">
    <button type="button" title="Remove" onclick="removeItem(this)">✕</button>`;
  row.querySelector("[name=description]").value = description;
  row.querySelector("[name=quantity]").value = quantity;
  row.querySelector("[name=unit_price]").value = price;
  document.getElementById("items").appendChild(row);
  updateTotal();
}

function removeItem(btn) {
  if (document.querySelectorAll("#items .item").length > 1) btn.parentElement.remove();
  updateTotal();
}

// Shows a live running total as the user types.
function updateTotal() {
  let subtotal = 0;
  document.querySelectorAll("#items .item").forEach(row => {
    const q = parseFloat(row.querySelector("[name=quantity]").value) || 0;
    const p = parseFloat(row.querySelector("[name=unit_price]").value) || 0;
    subtotal += q * p;
  });
  const tax = subtotal * (parseFloat(document.getElementById("tax_rate").value) || 0) / 100;
  const sym = document.getElementById("currency").selectedOptions[0].dataset.symbol;
  document.getElementById("total").textContent = "Total: " + sym + (subtotal + tax).toFixed(2);
}

// Picking a saved client fills in their name and address.
const picker = document.getElementById("client-picker");
if (picker) picker.addEventListener("change", () => {
  const opt = picker.selectedOptions[0];
  document.getElementById("client_name").value = opt.dataset.name || "";
  document.getElementById("client_details").value = opt.dataset.details || "";
});

document.addEventListener("input", updateTotal);
document.addEventListener("change", updateTotal);

// Rows to start with are passed in from the page as JSON in data-items.
const itemsBox = document.getElementById("items");
const startItems = JSON.parse(itemsBox.dataset.items || "[]");
if (startItems.length) startItems.forEach(i => addItem(i.description, i.quantity, i.unit_price));
else addItem();
