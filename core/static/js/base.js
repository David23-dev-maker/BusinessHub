
document.addEventListener("DOMContentLoaded", function () {

    const accountButton =
        document.getElementById("accountButton");

    const accountMenu =
        document.getElementById("accountMenu");

    const notificationContainer =
        document.getElementById(
            "notificationContainer"
        );

    const notificationButton =
        document.getElementById(
            "notificationButton"
        );

    const notificationMenu =
        document.getElementById(
            "notificationMenu"
        );

    const mobileMenuButton =
        document.getElementById(
            "mobileMenuButton"
        );

    const mobileMenu =
        document.getElementById(
            "mobileMenu"
        );


    /* ACCOUNT DROPDOWN */

    if (accountButton && accountMenu) {

        accountButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();
                event.stopPropagation();

                accountMenu.classList.toggle(
                    "open"
                );

            }
        );

    }


    /* NOTIFICATION DROPDOWN */

    if (
        notificationButton &&
        notificationMenu &&
        notificationContainer
    ) {

        notificationButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();
                event.stopPropagation();

                const isOpen =
                    notificationMenu.classList.contains(
                        "open"
                    );

                notificationMenu.classList.toggle(
                    "open",
                    !isOpen
                );

                notificationContainer.classList.toggle(
                    "open",
                    !isOpen
                );

                notificationButton.classList.toggle(
                    "active",
                    !isOpen
                );

                notificationButton.setAttribute(
                    "aria-expanded",
                    String(!isOpen)
                );

            }
        );

    }


    /* MOBILE MENU */

    if (mobileMenuButton && mobileMenu) {

        mobileMenuButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();
                event.stopPropagation();

                mobileMenu.classList.toggle(
                    "open"
                );

            }
        );

    }


    /* CLOSE MENUS WHEN CLICKING OUTSIDE */

    document.addEventListener(
        "click",
        function (event) {

            if (
                notificationContainer &&
                notificationButton &&
                notificationMenu &&
                !notificationContainer.contains(
                    event.target
                )
            ) {

                notificationMenu.classList.remove(
                    "open"
                );

                notificationContainer.classList.remove(
                    "open"
                );

                notificationButton.classList.remove(
                    "active"
                );

                notificationButton.setAttribute(
                    "aria-expanded",
                    "false"
                );

            }


            if (
                accountButton &&
                accountMenu &&
                !accountButton.contains(
                    event.target
                ) &&
                !accountMenu.contains(
                    event.target
                )
            ) {

                accountMenu.classList.remove(
                    "open"
                );

            }

        }
    );


    /* ESCAPE KEY */

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key !== "Escape") {
                return;
            }


            if (notificationMenu) {

                notificationMenu.classList.remove(
                    "open"
                );

            }


            if (notificationContainer) {

                notificationContainer.classList.remove(
                    "open"
                );

            }


            if (notificationButton) {

                notificationButton.classList.remove(
                    "active"
                );

                notificationButton.setAttribute(
                    "aria-expanded",
                    "false"
                );

            }


            if (accountMenu) {

                accountMenu.classList.remove(
                    "open"
                );

            }


            if (mobileMenu) {

                mobileMenu.classList.remove(
                    "open"
                );

            }

        }
    );


    /* CLOSE MOBILE MENU AFTER LINK CLICK */

    if (mobileMenu) {

        const mobileLinks =
            mobileMenu.querySelectorAll("a");

        mobileLinks.forEach(
            function (link) {

                link.addEventListener(
                    "click",
                    function () {

                        mobileMenu.classList.remove(
                            "open"
                        );

                    }
                );

            }
        );

    }

});


/*
 * BUSINESSHUB PWA
 *
 * Register the service worker.
 */

if (
    "serviceWorker" in navigator
) {

    window.addEventListener(
        "load",
        function () {

            navigator.serviceWorker
                .register(
                    "/static/pwa/service-worker.js"
                )
                .then(
                    function (registration) {

                        console.log(
                            "BusinessHub service worker registered:",
                            registration.scope
                        );

                    }
                )
                .catch(
                    function (error) {

                        console.error(
                            "BusinessHub service worker registration failed:",
                            error
                        );

                    }
                );

        }
    );

}
