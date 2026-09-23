document.addEventListener("DOMContentLoaded", () => {
    const list = document.getElementById("excluded-position-list");
    const addButton = document.getElementById("add-excluded-position");

    if (list === null || addButton === null) {
        return;
    }

    function addRemoveHandler(button) {
        button.addEventListener("click", () => {
            const fields = list.querySelectorAll(".dynamic-input");
            const wrapper = button.closest(".dynamic-input");

            if (wrapper === null) {
                return;
            }

            if (fields.length > 1) {
                wrapper.remove();
                return;
            }

            const input = wrapper.querySelector("input");

            if (input !== null) {
                input.value = "";
            }
        });
    }

    addButton.addEventListener("click", () => {
        const wrapper = document.createElement("div");
        wrapper.className = "dynamic-input";

        wrapper.innerHTML = `
            <input
                type="text"
                name="excluded position"
                placeholder="например: ба"
            >
            <button type="button" class="remove-field">
                Удалить
            </button>
        `;

        list.appendChild(wrapper);

        const removeButton = wrapper.querySelector(".remove-field");

        if (removeButton !== null) {
            addRemoveHandler(removeButton);
        }
    });

    list
        .querySelectorAll(".remove-field")
        .forEach(addRemoveHandler);
});
