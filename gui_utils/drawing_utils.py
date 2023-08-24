import numpy as np

seven_circle = np.array([[0,0,1,1,1,0,0],
                         [0,1,1,1,1,1,0],
                         [1,1,1,1,1,1,1],
                         [1,1,1,1,1,1,1],
                         [1,1,1,1,1,1,1],
                         [0,1,1,1,1,1,0],
                         [0,0,1,1,1,0,0]])

five_circle = np.array([[0,0,1,0,0],
                        [0,1,1,1,0],
                        [1,1,1,1,1],
                        [0,1,1,1,0],
                        [0,0,1,0,0]])

three_circle = np.array([[0,1,0],
                         [1,1,1],
                         [0,1,0]])

circles = {"1": 1, "3": three_circle, "5": five_circle, "7": seven_circle}
squares = {"1": 1, "3": np.ones((3, 3)), "5": np.ones((5, 5)), "7": np.ones((7, 7))}
