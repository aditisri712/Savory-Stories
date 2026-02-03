from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "savory_secret_key" 

def init_db():
    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS recipes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              ingredients TEXT,
              method TEXT,
              user_id INTEGER,
              FOREIGN KEY(user_id) REFERENCES users(id)
              )''')
    conn.commit()
    conn.close()

@app.route("/")
def login_page():
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, password))
        conn.commit()
        flash("Signup successful! Please login.", "success")
    except sqlite3.IntegrityError:
        flash("Email already exists!", "error")
    conn.close()
    return redirect(url_for("login_page"))

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = c.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        session["username"] = user[1]
        flash("Login successful!", "success")
        return redirect(url_for("home"))
    else:
        flash("Invalid credentials!", "error")
    return redirect(url_for("login_page"))

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    search_query = request.args.get('search')
    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    base_query = """
        SELECT recipes.id, recipes.title, recipes.description, recipes.image, users.username 
        FROM recipes 
        INNER JOIN users ON recipes.user_id = users.id
    """

    if search_query:
        final_query = base_query + " WHERE recipes.title LIKE ? OR recipes.description LIKE ?"
        c.execute(final_query, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        c.execute(base_query)
    
    rows = c.fetchall()

    all_recipes = []
    for row in rows: 
        all_recipes.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "image": row[3],
            "author": row[4] 
        })
    conn.close()

    return render_template("home.html", username=session["username"], recipes=all_recipes)

@app.route("/create", methods=["GET","POST"])
def create_recipes():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        ingredients = request.form["ingredients"]
        method = request.form["method"]

        file = request.files.get('image')
        filename = None

        if file and file.filename !='':
            filename = file.filename

            if not os.path.exist('static/uploads'):
                os.makedirs('static/uploads')
            file.save(os.path.join('static/uploads', filename))
  
        conn = sqlite3.connect("savory.db")
        c = conn.cursor()

        c.execute("INSERT INTO recipes (title, description, ingredients, method, user_id) VALUES (?, ?, ?, ?, ?)",
                  (title, description, ingredients, method, session["user_id"]))
        
        conn.commit()
        conn.close()
        flash("Recipe shared successfully!", "success")
        return redirect(url_for("home"))
    
    return render_template("create.html")

@app.route("/edit_recipe/<int:recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    conn = sqlite3.connect("savory.db")
    c = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        ingredients = request.form.get("ingredients")
        method = request.form.get("method")
        print(f"DEBUG: title={title}, desc={description}")
        
        if not title or not description:
            return "Error: Title and Description are required!", 400
       
        file = request.files.get('image')
        if file and file.filename != '':
            filename = file.filename
            file.save(os.path.join('static/uploads', filename))

            c.execute("""UPDATE recipes 
                         SET title=?, description=?, ingredients=?, method=?, image=? 
                         WHERE id=? AND user_id=?""", 
                      (title, description, ingredients, method, filename, recipe_id, session["user_id"]))
        else:
            filename = None
            c.execute("""UPDATE recipes 
                         SET title=?, description=?, ingredients=?, method=? 
                         WHERE id=? AND user_id=?""", 
                      (title, description, ingredients, method, recipe_id, session["user_id"]))
        
        conn.commit()
        conn.close()
        return redirect(url_for("profile"))

    c.execute("SELECT title, description, ingredients, method, image FROM recipes WHERE id=? AND user_id=?", (recipe_id, session["user_id"]))
    row = c.fetchone()
    conn.close()

    if row:
        recipe_data = {
            "title": row[0], 
            "description": row[1], 
            "ingredients": row[2], 
            "method": row[3], 
            "image": row[4]
        }
        return render_template("edit_recipe.html", recipe=recipe_data)
    
    return "Recipe not found or Unauthorized", 404

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route("/logout")
def logout():
    session.clear() 
    flash("You have been logged out.", "info")
    return redirect(url_for("login_page"))

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    c.execute("SELECT id, title, description, image FROM recipes WHERE user_id=?", (session["user_id"],))
    rows = c.fetchall()

    user_recipes =[]
    for row in rows:
        user_recipes.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "image": row[3]
            }) 
    conn.close()
    
    return render_template("profile.html", username=session["username"], recipes=user_recipes)

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    if request.method == "POST":
        new_username = request.form["username"]
        user_id = session["user_id"]

        conn = sqlite3.connect("savory.db")
        c = conn.cursor()
        
        c.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user_id))
        conn.commit()
        conn.close()
    
        session["username"] = new_username
        flash("Profile updated successfully!")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", username=session["username"])
 
@app.route("/delete/<int:recipe_id>")
def delete_recipe(recipe_id):
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    
    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    c.execute("DELETE FROM recipes WHERE id=? AND user_id=?", (recipe_id, session["user_id"]))
    conn.commit()
    conn.close()
    
    flash("Recipe deleted successfully!")
    return redirect(url_for("profile"))

def init_db():
    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    ingredients TEXT,
                    method TEXT,
                    image TEXT, 
                    user_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

@app.route("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id):
    conn = sqlite3.connect("savory.db")
    c = conn.cursor()
    c.execute("SELECT title, description, ingredients, method, image FROM recipes WHERE id=?", (recipe_id,))
    row = c.fetchone()
    conn.close()

    if row:
        recipe = {
            "title": row[0],
            "description": row[1],
            "ingredients": row[2],
            "method": row[3],
            "image": row[4]
        }
        return render_template("recipe_detail.html", recipe=recipe)
    return "Recipe not found!", 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)