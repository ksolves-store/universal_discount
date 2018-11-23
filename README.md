# Universal Discount

This application provides Odoo users with the feature to calculate Universal Discount on sale or purchase order.

# Features

-   Calculate total Discount value on sale/purchase order instead of doing the same on sale/purchase order lines as in regular Odoo process.
-   Universal Discount can be given in percentage or amount value.
-   Application function can be easily Enabled/Disabled from Odoo  Configuration.
-   Journal Entries are maintained with a separate line for Universal Discount values.
-   Refund entries are also maintained in Journal Entries.
-   Report printing of Sales, Purchase and Invoice are also maintained.
-   Compatible with Ksolves’ Universal Tax Application. 

** Note: When both the applications are installed together, then the Universal Tax will be applied on Universal Discount values.**

# Installation

-   There’s NO external library used.

# Configuration

After installing this module from Odoo  Apps, follow these steps to activate this application:

-   To View Universal Discount Setting :

    > Settings → General Settings → Invoicing

    ** Note: In order to enable this application, please Ensure that Accounting of at least one country is installed and selected in Fiscal Localizations in Invoice Settings.**

-   At the top, there will be Universal Discount settings where you have to check the box to Enable or Disable Universal Discount.

-   After enabling the Universal Discount, you have to define accounts to be used to maintain Universal Discount values.

-   After the above step is done, a field will appear or Universal Discount value in Sales, Purchase and Invoice model view.

-   After creating and validating the order, Journal Entries are created with separate Universal Discount lines in them.

      ** Note: To see the Journal Entries, you have to give the current user access to "Show Full Accounting Features" through Odoo  Settings → Users (in Debug mode).**


 # Authors

-   Developed and maintained by - [Ksolves India Pvt. Ltd.](https://www.ksolves.com/)


