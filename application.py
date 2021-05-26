from flask import Flask, render_template

import folium

app = Flask(__name__)

@app.route("/")
def index():

    folium_map = folium.Map(location=(-33, 151), zoom_start=12, width="90%", height="80%", left="5%", top="5%")
    folium_map.save("templates/map.html")
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)