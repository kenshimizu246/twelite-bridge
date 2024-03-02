import pytest


import serial
import time
from binascii import *
from struct import pack

import os
import time
import signal
import logging
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
import requests
from optparse import OptionParser

from PIL import Image
import cv2
import torch
from torch import nn
from torchvision import models, transforms
from time import sleep
import numpy as np

import twelite_django_bridge
import a

def test_missing_list():
    assert(1==1)



def test_a():
    a.a()
    assert(1==1)
