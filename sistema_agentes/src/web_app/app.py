from dotenv import load_dotenv
from src.web_app.app_config import Config
from src.web_app.agent_manager import AgentManager
from src.web_app.frontend_routes import bp
from quart import Quart

load_dotenv()

app = Quart(__name__)
app.register_blueprint(bp)

@app.before_serving
async def startup():
    """Initialize the AgentManager before serving requests"""
    agent_manager = AgentManager.get_instance()
    await agent_manager.initialize()

@app.after_serving
async def cleanup():
    """Cleanup the AgentManager after serving"""
    await AgentManager.clean()

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)