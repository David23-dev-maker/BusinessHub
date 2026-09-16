// =====================================================
// CATEGORY SEARCH
// =====================================================

const categorySearch = document.getElementById("categorySearch");
const categoryCards = document.querySelectorAll(".business-category");

if (categorySearch) {

    categorySearch.addEventListener("input", function () {

        const searchText = this.value.toLowerCase().trim();

        categoryCards.forEach(function (card) {

            const categoryName =
                card.getAttribute("data-name").toLowerCase();

            if (categoryName.includes(searchText)) {

                card.style.display = "flex";

            } else {

                card.style.display = "none";

            }

        });

    });

}
// =====================================================
// BUSINESS SEARCH + CATEGORY FILTER
// =====================================================

const businessSearch = document.getElementById("businessSearch");
const businessCategory = document.getElementById("businessCategory");
const businessCards = document.querySelectorAll(".business-card");

function filterBusinesses() {

    const searchText = businessSearch
        ? businessSearch.value.toLowerCase().trim()
        : "";

    const selectedCategory = businessCategory
        ? businessCategory.value
        : "all";

    businessCards.forEach(function (card) {

        const businessName =
            card.getAttribute("data-name").toLowerCase();

        const cardCategory =
            card.getAttribute("data-category").toLowerCase();

        const matchesSearch =
            businessName.includes(searchText);

        const matchesCategory =
            selectedCategory === "all" ||
            cardCategory === selectedCategory;

        if (matchesSearch && matchesCategory) {

            card.style.display = "block";

        } else {

            card.style.display = "none";

        }

    });
}


if (businessSearch) {

    businessSearch.addEventListener(
        "input",
        filterBusinesses
    );

}


if (businessCategory) {

    businessCategory.addEventListener(
        "change",
        filterBusinesses
    );

}