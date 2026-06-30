import subprocess


class ProcessService:

    @staticmethod
    def start_all():

        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "message": result.stdout
        }

    @staticmethod
    def stop_all():

        result = subprocess.run(
            ["docker-compose", "down"],
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "message": result.stdout
        }

    @staticmethod
    def restart_all():

        subprocess.run(["docker-compose", "down"])

        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "message": result.stdout
        }