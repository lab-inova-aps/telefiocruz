
import time
from slth.tasks import Task

class FazerAlgumaCoisa(Task):

    def __init__(self, n):
        self.n = n
        super().__init__()
    

    def run(self):
        for i in self.iterate(range(1, self.n)):
            print(i)
            if self.job.id == 5: 0/0
            time.sleep(1)
