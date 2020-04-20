var span = 250;
var prev = 0;
let input_text = document.getElementById("text");
let input_bps = document.getElementById("bps");
let transmitter = document.getElementById("transmit-box");
let clock = document.getElementById("clock-box");
let mode_label = document.getElementById("mode-label");
let settings_block = document.getElementById("settings-block");
let mode_select = document.getElementById("mode");
let settings_shown = false;
let clock_val = false;
function toggleClock(clock_enabled) {
    if (clock_enabled) {
        // Show clock div
        clock.style.display = "block";
        // Set height of containers
        transmitter.style.height = "45vh";
        clock.style.height = "45vh";
    } else {
        // Show clock div
        clock.style.display = "none";
        // Set height of containers
        transmitter.style.height = "90vh";
        // Change mode label
        mode_label.innerText = "BPS";
    }
}
function changeMode() {
    let mode = mode_select.value;
    if (mode.localeCompare("clock") == 0) {
        toggleClock(true);
    } else {
        toggleClock(false);
    }
}

function toggleSettings() {
    var disp = "block";
    if (settings_shown) {
        disp = "none"
    }
    settings_block.style.display = disp;
    settings_shown = !settings_shown;
}

function transmit() {
    let start_symbol = "11110011";
    let stop_symbol = stringToBytes('\n')[0];

    const text = input_text.value;

    span = 1000 / +input_bps.value;

    console.log("Used span: " + span);
    var bytes = [start_symbol];
    const strBytes = stringToBytes(text);
    for (let i = 0; i < strBytes.length; i++) {
        bytes.push(strBytes[i]);
    }
    bytes.push(stop_symbol);

    console.log(bytes);

    transmitBytes(bytes);
}
function transmitBytes_basic(bytes) {
    const bits = toBitArray(bytes);
    // Add bit to reset background
    bits.push("1")
    console.log(bits);

    for (let i = 0; i < bits.length; i++) {
        const bit = bits[i];

        setTimeout(function () {
            var diff = (prev == 0 ? span : Date.now() - prev);
            prev = Date.now()
            delay = span + (span - diff)

            var vis = (bit == '1' ? "white" : "black");
            transmitter.style.background = vis;

            console.log(`${prev} (diff=${diff}, delay=${delay}) Color set to ${vis}`)
        }, span * i)
    }
}
function transmitBytes_clock(bytes) {
    const bits = toBitArray(bytes);
    // Add bit to reset background
    bits.push("1")
    console.log(bits);

    for (let i = 0; i < bits.length; i++) {
        const bit = bits[i];

        setTimeout(function () {
            var diff = (prev == 0 ? span : Date.now() - prev);
            prev = Date.now()
            delay = span + (span - diff)

            var vis = (bit == '1' ? "white" : "black");
            transmitter.style.background = vis;

            var clock_color = "white";
            if(clock_val) {
                clock_color = "black";
            }
            clock.style.backgroundColor = clock_color;
            clock_val = !clock_val;


            console.log(`${prev} (diff=${diff}, delay=${delay}) Color set to ${vis}`)
        }, span * i)
    }
}
function transmitBytes_brightness(bytes) {
    const bits = toBitArray(bytes);
    // Add bit to reset background
    bits.push("1")
    bits.push("1")
    console.log(bits.length);

    for (let i = 0; i < bits.length; i += 2) {
        const bit = bits[i] + bits[i + 1];


        setTimeout(function () {
            var digit = parseInt(bit, 2);
            digit *= 85;

            console.log(digit)
            var diff = (prev == 0 ? span : Date.now() - prev);
            prev = Date.now()
            delay = span + (span - diff)

            var vis = "rgb(" + digit + ", " + digit + ", " + digit + ")";
            transmitter.style.background = vis;


            console.log(`${prev} (diff=${diff}, delay=${delay}) Color set to ${vis}`)
        }, span * i)
    }
}
function transmitBytes_brightness_clock(bytes) {
    const bits = toBitArray(bytes);
    // Add bit to reset background
    bits.push("1")
    console.log(bits.length);

    for (let i = 0; i < bits.length; i ++) {
        let clock_bit = "0";
        if(clock_val) {
            clock_bit = "1";
        }
        clock_val = !clock_val;
        const bit = clock_bit + bits[i];


        setTimeout(function () {
            var digit = parseInt(bit, 2);
            digit *= 85;

            console.log(digit)
            var diff = (prev == 0 ? span : Date.now() - prev);
            prev = Date.now()
            delay = span + (span - diff)

            var vis = "rgb(" + digit + ", " + digit + ", " + digit + ")";
            transmitter.style.background = vis;


            console.log(`${prev} (diff=${diff}, delay=${delay}) Color set to ${vis}`)
        }, span * i)
    }
}

function transmitBytes(bytes) {
    const mode = mode_select.value;
    if (mode.localeCompare("basic") == 0) {
        transmitBytes_basic(bytes);
    }
    else if (mode.localeCompare("clock") == 0) {
        transmitBytes_clock(bytes);
    }
    else if (mode.localeCompare("brightness") == 0) {
        transmitBytes_brightness(bytes);
    }
    else if(mode.localeCompare("br_clock") == 0) {
        transmitBytes_brightness_clock(bytes);
    }
}
function toBitArray(bytes) {
    let result = [];
    const hamming = document.getElementById("hamming_check").checked;
    let str = "";
    for(let i = 0; i < bytes.length; i++) {
        str += bytes[i];
    }
    if(hamming) {
        str = hammingEncode(str);
    }
    for(let i = 0; i < str.length; i++) {
        result.push(str[i])
    }
    return result;
}
function toBinary(val, pad_length = 8) {
    return (val).toString(2).padStart(pad_length, '0');
}

function stringToBytes(str) {
    return toUTF8Array(str).map(item => toBinary(item))
}
function toUTF8Array(str) {
    let utf8 = [];

    for (let i = 0; i < str.length; i++) {
        let charcode = str.charCodeAt(i);

        if (charcode < 0x80) {
            utf8.push(charcode);
        } else if (charcode < 0x800) {
            utf8.push(0xc0 | (charcode >> 6),
                0x80 | (charcode & 0x3f));
        } else if (charcode < 0xd800 || charcode >= 0xe000) {
            utf8.push(0xe0 | (charcode >> 12),
                0x80 | ((charcode >> 6) & 0x3f),
                0x80 | (charcode & 0x3f));
        } else {
            // surrogate pair
            i++;
            // UTF-16 encodes 0x10000-0x10FFFF by
            // subtracting 0x10000 and splitting the
            // 20 bits of 0x0-0xFFFFF into two halves
            charcode = 0x10000 + (((charcode & 0x3ff) << 10) |
                (str.charCodeAt(i) & 0x3ff));
            utf8.push(0xf0 | (charcode >> 18),
                0x80 | ((charcode >> 12) & 0x3f),
                0x80 | ((charcode >> 6) & 0x3f),
                0x80 | (charcode & 0x3f));
        }
    }

    return utf8;
}
function hammingEncode(input) {
	if (typeof input !== 'string' || input.match(/[^10]/)) {
		return console.error('hamming-code error: input should be binary string, for example "101010"');
	}

	var output = input;
	var controlBitsIndexes = [];
	var controlBits = [];
	var l = input.length;
	var i = 1;
	var key, j, arr, temp, check;

	while (l / i >= 1) {
		controlBitsIndexes.push(i);
		i *= 2;
	}

	for (j = 0; j < controlBitsIndexes.length; j++) {
		key = controlBitsIndexes[j];
		arr = output.slice(key - 1).split('');
		temp = chunk(arr, key);
		check = (temp.reduce(function (prev, next, index) {
			if (!(index % 2)) {
				prev = prev.concat(next);
			}
			return prev;
		}, []).reduce(function (prev, next) { return +prev + +next }, 0) % 2) ? 1 : 0;
		output = output.slice(0, key - 1) + check + output.slice(key - 1);
		if (j + 1 === controlBitsIndexes.length && output.length / (key * 2) >= 1) {
			controlBitsIndexes.push(key * 2);
		}
	}

	return output;
}

/**
 * chunk - split array into chunks
 * @param {Array} arr - array
 * @param {Number} size - chunk size
 * @returns {Array} - chunked array
 */
function chunk(arr, size) {
	var chunks = [],
	i = 0,
	n = arr.length;
	while (i < n) {
		chunks.push(arr.slice(i, i += size));
	}
	return chunks;
}