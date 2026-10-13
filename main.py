import sys
import os
import asyncio

if __name__ == "__main__":
    bot_dir = os.path.join(os.path.dirname(__file__), "Manager Bot")
    os.chdir(bot_dir)
    sys.path.insert(0, bot_dir)
    import main
    main.acquire_pid_lock()
    try:
        asyncio.run(main.main())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        main.release_pid_lock()
