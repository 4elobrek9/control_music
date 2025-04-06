import psutil
import time
import win32gui
import win32process
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from loguru import logger
import configparser

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

SETTINGS = config['SETTINGS']

SET_VOL = float(SETTINGS.get('set_vol', '0'))
NORMAL_VOL = float(SETTINGS.get('normal_vol', '100'))
CHECK_INTERVAL = 0.5
GAMES_FILE = 'games.txt'
music = SETTINGS.get('player_version', 'Свой вариант')

LANGUAGE = SETTINGS.get('language', 'ru')
WINDOW_X = int(SETTINGS.get('window_x', '1326'))
WINDOW_Y = int(SETTINGS.get('window_y', '436'))

class VolumeController:
    @staticmethod
    def set_volume(volume):
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name().lower() == music.lower():
                volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume_control.SetMasterVolume(volume / 100, None)
                logger.debug(f"Установлена громкость {volume}% для {music}")
                return True
        logger.warning(f"Процесс {music} не найден")
        return False


class ProcessMonitor:
    def __init__(self):
        self.blacklist = {
            "locationnotificationwindows.exe",
            "rzdiagnostic",
            "trustedinstaller.exe",
            "searchindexer.exe",
            "searchprotocolhost.exe",
            "monotificationux.exe",
            "EnumWindows",
            "rvcontrolsvc.exe"
        }

    def is_music_player_running(self):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'].lower() == music.lower():
                return True
        return False

    def is_game_running(self, games):
        false_positives = []

        for game in games:
            game_lower = game.lower()
            for process in psutil.process_iter(['name']):
                process_name = process.info['name'].lower()

                if process_name in self.blacklist:
                    continue

                if game_lower in process_name or process_name.startswith(game_lower):
                    logger.debug(f"Найден процесс: {process_name} (сопоставлен с игрой: {game})")
                    false_positives.append(process_name)

        if false_positives:
            logger.warning(f"Возможные ложные срабатывания: {', '.join(set(false_positives))}")
            with open('false_positives.txt', 'a', encoding='utf-8') as f:
                f.write(f"{time.ctime()}: {', '.join(set(false_positives))}\n")

        return len(false_positives) > 0

    def is_youtube_opened(self):
        try:
            browser_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() in ['chrome.exe', 'msedge.exe', 'firefox.exe']:
                    browser_processes.append(proc.info['pid'])

            def check_window(hwnd, pid):
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return False

                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid != pid:
                        return False

                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        return False

                    return (('youtube' in title.lower() or 'ютуб' in title.lower()) and 
                            (' - ' in title and ('chrome' in title.lower() or 
                             'edge' in title.lower() or 'firefox' in title.lower())))
                except:
                    return False

            for pid in browser_processes:
                try:
                    result = [False]

                    def callback(hwnd, param):
                        if check_window(hwnd, param):
                            result[0] = True
                            return False
                        return True

                    win32gui.EnumWindows(callback, pid)
                    if result[0]:
                        return True

                except Exception as e:
                    logger.debug(f"Ошибка при проверке PID {pid}: {e}")
                    continue

            return False

        except Exception as e:
            logger.error(f"Ошибка в is_youtube_opened: {e}")
            return False


class AppController:
    def __init__(self):
        self.monitor = ProcessMonitor()
        self.games = self.load_games()
        self.last_state = None

    def load_games(self):
        try:
            with open(GAMES_FILE, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            logger.error(f"Файл {GAMES_FILE} не найден. Создан новый файл.")
            with open(GAMES_FILE, 'w', encoding='utf-8') as file:
                file.write("")
            return []

    def run(self):
        logger.info(f"Запуск приложения с настройками: player={music}, set_vol={SET_VOL}, normal_vol={NORMAL_VOL}")
        
        while True:
            try:
                player_running = self.monitor.is_music_player_running()
                youtube_opened = self.monitor.is_youtube_opened()
                game_running = self.monitor.is_game_running(self.games)

                current_state = {
                    'player': player_running,
                    'youtube': youtube_opened,
                    'game': game_running
                }

                if current_state != self.last_state:
                    if not player_running:
                        logger.debug(f"{music} не запущен")
                    elif youtube_opened or game_running:
                        VolumeController.set_volume(SET_VOL)
                        logger.info(f"Тихий режим | YouTube: {youtube_opened} | Игра: {game_running}")
                    else:
                        VolumeController.set_volume(NORMAL_VOL)
                        logger.info("Нормальная громкость")

                    self.last_state = current_state

                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Критическая ошибка: {e}")
                time.sleep(1)


if __name__ == "__main__":
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    if LANGUAGE == 'ru':
        log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"

    logger.add(
        "app.log",
        format=log_format,
        rotation="1 MB",
        retention="10 days",
        encoding='utf-8'
    )

    logger.info(f"Инициализация приложения. Язык: {LANGUAGE}")
    app = AppController()
    app.run()
    