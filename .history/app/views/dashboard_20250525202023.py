from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session
from flask_login import login_required, login_user, logout_user, LoginManager
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Configuración simple de autenticación
DASHBOARD_USERS = {
    'admin': 'pbkdf2:sha256:260000$xK2L6RqF$8f3e5c...'  # Generar con generate_password_hash
}

@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in DASHBOARD_USERS and check_password_hash(DASHBOARD_USERS[username], password):
            session['user'] = username
            return redirect(url_for('dashboard.index'))
            
    return render_template('login.html')

@dashboard_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('dashboard.login'))

@dashboard_bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('dashboard.html')

@dashboard_bp.route('/api/stats')
def get_stats():
    """API endpoint para estadísticas en tiempo real."""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    from app.core.session import session_manager
    from app import current_app
    
    # Estadísticas generales
    stats = {
        'active_sessions': len(session_manager.sessions),
        'total_messages_today': 0,
        'tickets_created_today': 0,
        'leads_created_today': 0,
        'avg_response_time': 0,
        'queue_stats': {}
    }
    
    # Contar mensajes de hoy
    today = datetime.now().date()
    for session in session_manager.sessions.values():
        for msg in session.get('message_history', []):
            msg_date = datetime.fromisoformat(msg.get('timestamp', '')).date()
            if msg_date == today:
                stats['total_messages_today'] += 1
                
    # Estadísticas de colas si Redis está disponible
    if hasattr(current_app, 'queue_manager'):
        stats['queue_stats'] = current_app.queue_manager.get_queue_stats()
        
    return jsonify(stats)

@dashboard_bp.route('/api/sessions')
def get_sessions():
    """Lista todas las sesiones activas."""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    from app.core.session import session_manager
    
    sessions_data = []
    for wa_id, session_data in session_manager.sessions.items():
        sessions_data.append({
            'wa_id': wa_id,
            'name': session_data.get('message_history', [{}])[0].get('name', 'Unknown'),
            'state': session_data.get('state', 'UNKNOWN'),
            'created_at': session_data.get('created_at').isoformat(),
            'last_activity': session_data.get('last_activity').isoformat(),
            'messages_count': len(session_data.get('message_history', []))
        })
        
    return jsonify(sessions_data)

@dashboard_bp.route('/api/session/<wa_id>')
def get_session_detail(wa_id):
    """Detalles de una sesión específica."""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    from app.core.session import session_manager
    
    session_data = session_manager.sessions.get(wa_id)
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
        
    return jsonify({
        'wa_id': wa_id,
        'state': session_data.get('state'),
        'context': session_data.get('context'),
        'created_at': session_data.get('created_at').isoformat(),
        'last_activity': session_data.get('last_activity').isoformat(),
        'message_history': session_data.get('message_history', [])
    })

@dashboard_bp.route('/api/conversations')
def get_conversations():
    """Obtiene conversaciones recientes del log."""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conversations = []
    try:
        with open('logs/conversations.jsonl', 'r') as f:
            for line in f:
                conv = json.loads(line)
                conversations.append(conv)
        
        # Ordenar por timestamp y limitar
        conversations.sort(key=lambda x: x['timestamp'], reverse=True)
        conversations = conversations[:100]  # Últimas 100
        
    except FileNotFoundError:
        pass
        
    return jsonify(conversations)

@dashboard_bp.route('/api/metrics')
def get_metrics():
    """Métricas detalladas del sistema."""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    from app.utils.helpers import extract_metrics
    from app import current_app
    
    metrics = extract_metrics()
    
    # Agregar estado de circuit breakers si están disponibles
    if hasattr(current_app, 'circuit_breakers'):
        metrics['circuit_breakers'] = {}
        for name, cb in current_app.circuit_breakers.items():
            metrics['circuit_breakers'][name] = cb.get_status()
            
    return jsonify(metrics)