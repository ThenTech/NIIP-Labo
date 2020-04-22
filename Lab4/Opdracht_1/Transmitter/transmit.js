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
/**
 * Hide or show the clock div
 * @param {*} clock_enabled 
 */
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
/**
 * Check if the clock div has to be enabled
 */
function changeMode() {
    let mode = mode_select.value;
    if (mode.localeCompare("clock") == 0) {
        toggleClock(true);
    } else {
        toggleClock(false);
    }
}

/**
 * Show / hide the settings section
 */
function toggleSettings() {
    var disp = "block";
    if (settings_shown) {
        disp = "none"
    }
    settings_block.style.display = disp;
    settings_shown = !settings_shown;
}

/**
 * Transmit the bytes via LiFi
 */
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
/**
 * Basic transmission of the bytes
 * @param {} bytes 
 */
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
/**
 * Transmission of the bytes with clock enabled (extra div)
 * @param {} bytes 
 */
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
/**
 * Transmission of bytes by transmitting 
 * 2 bits at a time
 * @param {*} bytes 
 */
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
/**
 * Transmission of the bytes by using the 
 * brightness as a clock (no extra div)
 * @param {*} bytes 
 */
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

/**
 * Selects the right procedure to transmit the bytes
 * @param {*} bytes 
 */
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
/**
 * Convert the bytes to a bit array
 * Apply Hamming if enabled
 * @param {*} bytes 
 */
function toBitArray(bytes) {
    let result = [];
    const hamming = document.getElementById("hamming_check").checked;
    let str = "";
    for(let i = 0; i < bytes.length; i++) {
        str += bytes[i];
    }
    if(hamming) {
        const extraParity = document.getElementById("parity_check").checked;
        str = hammingEncodeData(str, extraParity);
    }
    for(let i = 0; i < str.length; i++) {
        result.push(str[i])
    }
    return result;
}
function hammingEncodeData(data, addExtra = false) {
    if(data.length % 4 != 0) {
        console.log("Can't encode nibbles")
    }
    let result = ""
    for(let i = 0; i < data.length; i+=4) {
        let str = "";
        for(let j = i; j < i + 4; j++) {
            str += data[j]
        }
        let encoded = hammingEncode(str)
        if(addExtra) {
            encoded += parityBit(encoded)
        }
        console.log("Encoding '" + str + "' gave '" + encoded + "'")
        result += encoded;
    }
    return result
}
function parityBit(bin='', parity = 'e'){
    function bitCount(bin){
        return (bin.match(/1/g) || []).length;
    }
    
    let isEven = bitCount(bin) % 2 === 0;
    if(parity.match(/^e$|^even$/i)) return isEven ? '0' : '1';
    return isEven ? '1' : '0';
}
/**
 * Convert to binary
 * @param {*} val 
 * @param {*} pad_length 
 */
function toBinary(val, pad_length = 8) {
    return (val).toString(2).padStart(pad_length, '0');
}
/**
 * Convert string to bytes
 * @param {*} str 
 */
function stringToBytes(str) {
    return toUTF8Array(str).map(item => toBinary(item))
}
/**
 * Appy UTF8 encoding to a string
 * @param {*} str 
 */
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
/**
 * hammingEncode - encode binary string input with hamming algorithm
 * @param {String} input - binary string, '10101'
 * @returns {String} - encoded binary string
 */
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
 * hammingPureDecode - just removes from input parity check bits
 * @param {String} input - binary string, '10101'
 * @returns {String} - decoded binary string
 */
function hammingPureDecode(input) {
	if (typeof input !== 'string' || input.match(/[^10]/)) {
		return console.error('hamming-code error: input should be binary string, for example "101010"');
	}

	var controlBitsIndexes = [];
	var l = input.length;
	var originCode = input;
	var hasError = false;
	var inputFixed, i;
	
	i = 1;
	while (l / i >= 1) {
		controlBitsIndexes.push(i);
		i *= 2;
	}

	controlBitsIndexes.forEach(function (key, index) {
		originCode = originCode.substring(0, key - 1 - index) + originCode.substring(key - index);
	});

	return originCode;
}

/**
 * hammingDecode - decodes encoded binary string, also try to correct errors
 * @param {String} input - binary string, '10101'
 * @returns {String} - decoded binary string
 */
function hammingDecode(input) {
	if (typeof input !== 'string' || input.match(/[^10]/)) {
		return console.error('hamming-code error: input should be binary string, for example "101010"');
	}

	var controlBitsIndexes = [];
	var sum = 0;
	var l = input.length;
	var i = 1;
	var output = hammingPureDecode(input);
	var inputFixed = hammingEncode(output);


	while (l / i >= 1) {
		controlBitsIndexes.push(i);
		i *= 2;
	}

	controlBitsIndexes.forEach(function (i) {
		if (input[i] !== inputFixed[i]) {
			sum += i;
		}
	});

	if (sum) {
		output[sum - 1] === '1' 
			? output = replaceCharacterAt(output, sum - 1, '0')
			: output = replaceCharacterAt(output, sum - 1, '1');
	}
	return output;
}

/**
 * hammingCheck - check if encoded binary string has errors, returns true if contains error
 * @param {String} input - binary string, '10101'
 * @returns {Boolean} - hasError
 */
function hammingCheck(input) {
	if (typeof input !== 'string' || input.match(/[^10]/)) {
		return console.error('hamming-code error: input should be binary string, for example "101010"');
	}

	var inputFixed = hammingEncode(hammingPureDecode(input));

	return hasError = !(inputFixed === input);
}

/**
 * replaceCharacterAt - replace character at index
 * @param {String} str - string
 * @param {Number} index - index
 * @param {String} character - character 
 * @returns {String} - string
 */
function replaceCharacterAt(str, index, character) {
  return str.substr(0, index) + character + str.substr(index+character.length);
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

