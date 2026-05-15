from prompt_optimizer_app.config import load_config
from prompt_optimizer_app.logging_setup import configure_logging
from prompt_optimizer_app.tray import PromptOptimizerTrayApp


def main() -> None:
    configure_logging()
    config = load_config()
    app = PromptOptimizerTrayApp(config)
    app.run()


if __name__ == "__main__":
    main()
