import requests

class CanvasAPI:

    paging = "?per_page=100"

    def __init__(self, token):
        self.base_url = token.type.base_url
        if not token:
            raise ValueError("Token is required")
        self.headers = {
            "Authorization": f"Bearer {token.value}"
        }

    def check_connection(self):
        """
        Check if the connection to the Canvas API is working
        """
        url = f"{self.base_url}/users/self"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status

    def get_user_courses(self, course_id=None):
        """
        Get all courses for the user
        or a specific course if course_id is provided
        """
        if course_id:
            url = f"{self.base_url}/courses/{course_id}{self.paging}"
        else:
            url = f"{self.base_url}/courses{self.paging}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()       
    
    def get_course_students(self, course_id):
        """
        Get all the students for a course
        """
        url = f"{self.base_url}/courses/{course_id}/students{self.paging}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_course_teachers(self, course_id):
        """
        Get all the teachers for a course
        """
        url = f"{self.base_url}/courses/{course_id}/search_users?enrollment_type=teacher&{self.paging[1:]}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_course_assignments(self, course_id, assignment_id=None):
        """
        Get all assignments for a course
        or a specific assignment if assignment_id is provided
        """
        if assignment_id:
            url = f"{self.base_url}/courses/{course_id}/assignments/{assignment_id}{self.paging}"
        else:
            url = f"{self.base_url}/courses/{course_id}/assignments{self.paging}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_course_grades(self, course_id):
        """
        Get all grades for a course
        """
        url = f"{self.base_url}/courses/{course_id}/grades{self.paging}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
