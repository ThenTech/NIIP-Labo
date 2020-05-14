import math
def get_distance(signalLvl, freq):
    exp = (27.55 - (20 * math.log10(freq)) + abs(signalLvl)) / 20
    return math.pow(10, exp)

def getDistanceFromAP(signalStrength):
        beta_numerator = float(-41-signalStrength)
        beta_denominator = float(10*3)
        beta = beta_numerator/beta_denominator
        distanceFromAP = round(((10**beta)*2.5),4)
        return distanceFromAP
def get_fspl(dist, freq):
    fspl = 20 * math.log10(dist) + 20 * math.log10(freq) - 27.55
    return fspl


dist = get_distance(-53, 2412)
dist2 = getDistanceFromAP(-83)
print(dist)