import os
from pks.dashboard import init_dashboard


# Initialize Dash app directly
app = init_dashboard(route="/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
