from prompt_optimizer_app.config import load_config
from prompt_optimizer_app.logging_setup import configure_logging
from prompt_optimizer_app.single_instance import SingleInstance
from prompt_optimizer_app.tray import PromptOptimizerTrayApp


def main() -> None:
    configure_logging()
    config = load_config()
    dashboard_url = f"http://{config.dashboard_host}:{config.dashboard_port}"
    single_instance = SingleInstance()
    if not single_instance.acquire(dashboard_url):
        return

    app = PromptOptimizerTrayApp(config)
    try:
        app.run()
    finally:
        single_instance.release()


if __name__ == "__main__":
    main()
