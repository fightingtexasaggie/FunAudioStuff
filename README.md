# FunAudioStuff
Windchimes and other fun toys

# Windchimes

Windchimes2.py is partially based on a paper:  T. Lukkari and V. Valimaki, "Modal synthesis of wind
chime sounds with stochastic event triggering," Proceedings of the 6th Nordic Signal Processing Symposium,
2004. NORSIG 2004., 2004, pp. 212-215.

It is set to the default key of E major pentonic, because I like it. You can pass a --scale argument
to set it to one of the more common windchime scales.

Set the latitude and longitude of the location you want to detect winds in. The default is set to
Corpus Christi, Texas USA, my hometown. The args are --lat and --lon and accept decimal degrees.

It runs under Linux with the Alsa sound system, and I'm running it on a Raspbian-based Pi 3 as well
as a Fedora 44 desktop. You'll have to fiddle with the aplay -l detection section to fit your soundcard
if not using some sort of USB audio.

Disclaimer: This thing is 99% Claude 5 generated, with a lot of interactive nitpicking by me. I'm currently
using the Vibraphone from the Alexi\_GM.sf2 soundfont available at:
https://archive.org/download/541-soundfonts-full-gm-sets/541-soundfonts-full-gm-sets/541\_Soundfonts\_Full\_GM\_Sets/
although I'd like to find a soundfont that accurately reproduces the tones of very large (and expensive)
tubular windchimes.

