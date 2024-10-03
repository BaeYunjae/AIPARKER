import pandas as pd
import numpy as np

def getDistance1(height):
    coefficients1 = [2.89171349e-05, -8.26735825e-03, 8.98101509e-01, -4.57842714e+01, 1.07120384e+03]
    polynomial1 = np.poly1d(coefficients1)
    return polynomial1(height)

def getDistance2(height):
    coefficients2 = [-2.73801559e-09, 1.87468034e-06, 2.31253402e-04, -4.46904122e-01, 1.11581926e+02]
    polynomial2 = np.poly1d(coefficients2)
    return polynomial2(height)

def getDistance3(height):
    coefficients3 = [-2.90722488e-06, 3.43521871e-03, -1.38194088e+00, 2.20474910e+02]
    polynomial3 = np.poly1d(coefficients3)
    return polynomial3(height)
