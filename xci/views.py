from xci import app, competency
from flask import render_template, redirect, flash, url_for, request, make_response
from forms import LoginForm, RegistrationForm, FrameworksForm, SettingsForm
from models import User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import json

login_manager = LoginManager()
login_manager.init_app(app)

mongo = MongoClient()
db = mongo.xci

@login_manager.user_loader
def load_user(user):
    if isinstance(user, basestring):
        userobj = User(user, 'get')
        u_id = userobj.get_id()
        return userobj
    else:
        u_id = user.get_id()
        return user

@app.route('/', methods=['GET'])
def index():
    uri = request.args.get('uri', None)
    if uri:
        p = competency.parseComp(uri)
        try:
            resp = make_response(json.dumps(p), 200)
            resp.headers['Content-Type'] = "application/json"
            return resp
        except Exception as e:
            return make_response("%s<br>%s" % (str(e), p), 200)
            # return make_response("fail <br> %s" % repr(p), 200)

    return '''yay we dids it! 
              <br>DEBUG: %s 
              <br>SECRET: %s
              <br><a href="./?uri=http://adlnet.gov/competency-framework/scorm/choosing-an-lms">choose lms</a>
              <br><a href="./?uri=http://adlnet.gov/competency-framework/computer-science/basic-programming">programming</a>
              <br><a href="./?uri=http://12.109.40.34/performance-framework/xapi/tetris">perf tetris</a>''' % (app.config['DEBUG'], app.config['SECRET_KEY'])

    # return render_template('home.html')
    
@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html', login_form=LoginForm())
    else:
        lf = LoginForm(request.form)
        if lf.validate_on_submit():
            user = User(lf.username.data, generate_password_hash(lf.password.data))
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", login_form=lf)

@app.route('/sign_up', methods=["GET", "POST"])
def sign_up():
    if request.method == 'GET':
        return render_template('sign_up.html', signup_form=RegistrationForm(), hide=True)
    else:
        rf = RegistrationForm(request.form)
        if rf.validate_on_submit():
            users = db.userprofiles
            users.insert({'username': rf.username.data, 'password':generate_password_hash(rf.password.data), 'email':rf.email.data,
                'first_name':rf.first_name.data, 'last_name':rf.last_name.data, 'competencies':[], 'compfwks':[], 'lrsprofiles':[]})
            
            user = User(rf.username.data, generate_password_hash(rf.password.data))
            login_user(user)
            return redirect(url_for('index'))
        return render_template('sign_up.html', signup_form=rf, hide=True)

@app.route('/frameworks', methods=["GET", "POST"])
def frameworks():
	if request.method == 'GET':
		return_dict = {'frameworks_form': FrameworksForm()}
	else:
		ff = FrameworksForm(request.form)
		if ff.validate_on_submit():
			try:
				#add to system
				pass
			except Exception, e:
				raise e
			return_dict = {'frameworks_form': FrameworksForm()}
		else:
			return_dict = {'frameworks_form': ff}

	return_dict['cfwks'] = competency.get_all_comp_frameworks()
	return render_template('frameworks.html', **return_dict)

@app.route('/me', methods=["GET"])
@login_required
def me():
	username = current_user.id
	user = db.userprofiles.find_one({'username':username})
	user_comps = user['competencies']
	# user_profiles = user['lrsprofiles']

	# completed_comps = [c for c in user_comps if c['completed'] == True].count()
	completed_comps = sum(1 for c in user_comps if c['completed'])
	started_comps = len(user_comps) - completed_comps	
	name = user['first_name'] + ' ' + user['last_name']

	return render_template('me.html', comps=user_comps, completed=completed_comps, started=started_comps, name=name, email=user['email'])

@app.route('/me/<comp_id>', methods=["GET"])
@login_required
def me_comp(comp_id):
	me = current_user
	return render_template('mycomp.html', comp_id=comp_id)

@app.route('/me/settings', methods=["GET"])
@login_required
def me_settings():
    username = current_user.id
    user = db.userprofiles.find_one({'username':username})
    user_profiles = user['lrsprofiles']
    
    return render_template('mysettings.html', user_profiles=user_profiles)

@app.route('/me/settings/update_endpoint', methods=["POST"])
@login_required
def update_endpoint():
    username = current_user.id
    #Werkzeug returns immutabledict object when multiple forms are on page. have to copy to get values
    sf = request.form.copy()
    
    default = False
    if 'default' in sf.keys():
        default = True

    user = db.userprofiles.find_one({'username':username})
    for profile in user['lrsprofiles']:
        if profile['name'] == sf['name']:
            profile['endpoint'] = sf['endpoint']
            profile['auth'] = sf['auth']
            profile['password'] = generate_password_hash(sf['password'])
            profile['default'] = default
        elif not profile['name'] == sf['name'] and default:
            profile['default'] = False

    db.userprofiles.update({'username':username}, user)

    # db.userprofiles.update({'username':username, 'lrsprofiles.name': sf['name']}, {'$set':{'name':sf['name'],'endpoint':sf['endpoint'], 'auth':sf['auth'],
    #     'password': generate_password_hash(sf['password']), 'default':default}})

    return redirect(url_for('me'))

@app.route('/me/settings/add_endpoint', methods=["POST"])
@login_required
def add_endpoint():
    username = current_user.id
    af = request.form.copy()
    user = db.userprofiles.find_one({'username':username})

    existing_names = [p['name'] for p in user['lrsprofiles']]

    if af['newname'] in existing_names:
        pass
    else:
        new_prof = {}
        default = False
        if 'newdefault' in af.keys():
            default = True

        new_prof['name'] = af['newname']
        new_prof['endpoint'] = af['newendpoint']
        new_prof['auth'] = af['newauth']
        new_prof['password'] = generate_password_hash(af['newpassword'])
        new_prof['default'] = default


        if default:
            for profile in user['lrsprofiles']:
                profile['default'] = False

        user['lrsprofiles'].append(new_prof)
        db.userprofiles.update({'username':username}, user)
    
    return redirect(url_for('me'))