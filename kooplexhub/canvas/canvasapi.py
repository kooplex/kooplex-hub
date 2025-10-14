import requests

from hub.api import ExternalAPI

class CanvasAPI(ExternalAPI):

    paging = "?per_page=100"

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token_value}"
        }

    @property
    def url_check(self):
        return f"{self.base_url}/users/self"


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
