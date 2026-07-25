export default function CreateItemForm(props) {
  const [state, setState] = React.useState("idle");

  if (state === "loading") {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-white bg-white"></div>
      </div>
    );
  } else if (state === "error") {
    return (
      <div className="bg-red-100 p-4 my-4 text-sm text-red-700">
        Something went wrong. Please try again.
      </div>
    );
  } else if (state === "success") {
    return (
      <div className="bg-green-100 p-4 my-4 text-sm text-green-700">
        Item created successfully!
      </div>
    );
  }

  return (
    <form>
      {(state !== "loading" && state !== "error" && state !== "success") && (
        <label
          htmlFor="itemName"
          className="block mb-2 text-sm font-bold"
        >
          Item Name:
        </label>
      )}
      {state === "idle" && (
        <input
          type="text"
          id="itemName"
          value={props.itemName}
          placeholder="Enter item name"
          className="block w-full p-2 pl-10 text-sm text-gray-700 border border-gray-200 rounded-md focus:outline-none focus:border-indigo-500"
        />
      )}
      {(state === "idle" || state === "success") && (
        <label
          htmlFor="itemDescription"
          className="block mb-2 text-sm font-bold"
        >
          Item Description:
        </label>
      )}
      {state === "idle" && (
        <textarea
          id="itemDescription"
          value={props.itemDescription}
          placeholder="Enter item description"
          className="block w-full p-2 pl-10 text-sm text-gray-700 border border-gray-200 rounded-md focus:outline-none focus:border-indigo-500"
        />
      )}
      {(state === "idle" || state === "success") && (
        <label
          htmlFor="itemPrice"
          className="block mb-2 text-sm font-bold"
        >
          Item Price:
        </label>
      )}
      {state === "idle" && (
        <input
          type="text"
          id="itemPrice"
          value={props.itemPrice}
          placeholder="Enter item price"
          className="block w-full p-2 pl-10 text-sm text-gray-700 border border-gray-200 rounded-md focus:outline-none focus:border-indigo-500"
        />
      )}
      {(state === "idle" || state === "success") && (
        <label
          htmlFor="itemStockQuantity"
          className="block mb-2 text-sm font-bold"
        >
          Item Stock Quantity:
        </label>
      )}
      {state === "idle" && (
        <input
          type="text"
          id="itemStockQuantity"
          value={props.itemStockQuantity}
          placeholder="Enter item stock quantity"
          className="block w-full p-2 pl-10 text-sm text-gray-700 border border-gray-200 rounded-md focus:outline-none focus:border-indigo-500"
        />
      )}
      {(state === "idle" || state === "success") && (
        <label
          htmlFor="itemSKU"
          className="block mb-2 text-sm font-bold"
        >
          Item SKU:
        </label>
      )}
      {state === "idle" && (
        <input
          type="text"
          id="itemSKU"
          value={props.itemSKU}
          placeholder="Enter item SKU"
          className="block w-full p-2 pl-10 text-sm text-gray-700 border border-gray-200 rounded-md focus:outline-none focus:border-indigo-500"
        />
      )}
      {state === "idle" && (
        <button
          onClick={(e) => setState("loading")}
          className="bg-orange-500 hover:bg-orange-700 text-white font-bold py-2 px-4 rounded-full"
        >
          Create Item
        </button>
      )}
    </form>
  );
}