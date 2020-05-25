import math
class Point:
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y

    def __str__(self):
        return "(" + ", ".join(map(lambda x: f"{round(x, 2):+5.2f}", (self.x, self.y))) + ")"

    def __eq__(self, value):
        return self.x == value.x and self.y == value.y

    def distance_to(self, p):
        if not isinstance(p, Point):
            raise Exception("[Point::distance_to] Argument is not a point!")

        return ((self.x - p.x) ** 2 + (self.y - p.y) ** 2) ** 0.5


class Quality:
    TAG_PERCENTAGE = 0
    TAG_DBM        = 1

    VALUE_COUNT = 6

    def __init__(self, value=0, tag=TAG_PERCENTAGE):
        self.tag = tag

        self.average   = 0
        self.avg_idx   = 0
        self.avg_sum   = 0
        self.avg_cache = [0.0] * Quality.VALUE_COUNT

    def get(self):
        return self.average

    def is_percentage(self):
        return self.tag == Quality.TAG_PERCENTAGE

    def is_dbm(self):
        return self.tag == Quality.TAG_DBM

    def update(self, new_value):
        self.avg_sum -= self.avg_cache[self.avg_idx]   # Remove oldest measurement
        self.avg_cache[self.avg_idx] = new_value

        self.avg_sum += new_value
        self.avg_idx += 1

        if self.avg_idx == Quality.VALUE_COUNT:
            # Only update after SIZE measurements, else avg is < SIZE numbers / SIZE and lower than expected
            self.average = self.avg_sum / Quality.VALUE_COUNT
            self.avg_idx = 0


class Position:
    def __init__(self, name, point, radius):
        super().__init__()

        if not isinstance(point, Point):
            raise Exception("[Point::distance_to] Argument is not a point!")

        self.name     = name
        self.location = point
        self.radius   = radius

    def __str__(self):
        return f"<Position {self.name} @ {self.location}, r={self.radius}>"

    __repr__ = __str__

    def intersection(self, p2, p3):
        return self._calc_intersetion(
            self.location, self.radius,
            p2.location  , p2.radius,
            p3.location  , p3.radius
        )
    def get_intersection(self, p2, p3):
        intersection = self._calc_intersetion(self.location, self.radius, p2.location, p2.radius, p3.location, p3.radius)
        p1_1, p1_2 = self._calc_intersection_with_circle(self.location, self.radius, p2.location, p2.radius)
        p2_1, p2_2 = self._calc_intersection_with_circle(self.location, self.radius, p3.location, p3.radius)
        p3_1, p3_2 = self._calc_intersection_with_circle(p2.location, p2.radius, p3.location, p3.radius)
        positions = [p1_1, p1_2, p2_1, p2_2, p3_1, p3_2]
        result = intersection
        min_dist = math.inf
        for p in positions:
            dist = p.distance_to(intersection)
            if dist < min_dist:
                min_dist = dist
                result = p 
        return p

    @staticmethod
    def _calc_intersection_with_circle(p1, r1, p2, r2):
        x0 = p1.x
        y0 = p1.y 
        x1 = p2.x 
        y1 = p2.y 

        d = math.sqrt((x1-x0)**2 + (y1-y0)**2)

        #No intersection
        if d > r1 +r2:
            return None 
        # One circle within other 
        if d < abs(r1-r2):
            return None
        if d == 0 and r0 == r1:
            return None 
        
        else: 
            a = (r1**2 - r2 ** 2 + d**2)/(2*d)
            h = math.sqrt(r1**2 - a**2)
            x2=x0+a*(x1-x0)/d   
            y2=y0+a*(y1-y0)/d   
            x3=x2+h*(y1-y0)/d     
            y3=y2-h*(x1-x0)/d 

            x4=x2-h*(y1-y0)/d
            y4=y2+h*(x1-x0)/d

            return (Point(x3,y3), Point(x4, y4))



    @staticmethod
    def _calc_intersetion(p1, r1, p2, r2, p3, r3):
        """https://www.101computing.net/cell-phone-trilateration-algorithm/"""

        A = 2 * p2.x - 2 * p1.x
        B = 2 * p2.y - 2 * p1.y
        C = r1**2 - r2**2 - p1.x**2 + p2.x**2 - p1.y**2 + p2.y**2
        D = 2 * p3.x - 2 * p2.x
        E = 2 * p3.y - 2 * p2.y
        F = r2**2 - r3**2 - p2.x**2 + p3.x**2 - p2.y**2 + p3.y**2
        x = (C*E - F*B) / (E*A - B*D)
        y = (C*D - A*F) / (B*D - A*E)

        return Point(x, y)


if __name__ == "__main__":
    """
        Test plot: https://www.desmos.com/calculator/q448t0j7vx
    """
    zero  = Point(0, 0)
    onexy = Point(1, 1)
    onex  = Point(1, 0)

    print(zero.distance_to(onexy) == 2**0.5)
    print(zero.distance_to(onex) == 1)

    center = Position("center", zero, 0.5)
    onedxy = Position("onedxy", onexy, 0.5)
    onedx  = Position("onedx", onex, 0.5)

    print(center.intersection(onedxy, onedx) == Point(0.5, 0.5))
