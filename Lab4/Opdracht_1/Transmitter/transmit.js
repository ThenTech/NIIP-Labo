var span = 250;
var prev = 0;
let input_text  = document.getElementById("text");
let input_bps   = document.getElementById("bps");
let transmitter = document.getElementById("transmit-box");
let clock = document.getElementById("clock-box");
let mode_label = document.getElementById("mode-label");
let clock_enabled = false;
function toggleClock() {
    if(!clock_enabled) {
        // Show clock div
        clock.style.display = "block";
        // Set height of containers
        transmitter.style.height = "45vh";
        clock.style.height = "45vh";
        // Change mode label
        mode_label.innerText = "Clock"
        // Hide bps box
        input_bps.style.display = "none";
        // Set boolean
        clock_enabled = true;
    } else {
        // Show clock div
        clock.style.display = "none";
        // Set height of containers
        transmitter.style.height = "90vh";
        // Change mode label
        mode_label.innerText = "BPS"
        // Hide bps box
        input_bps.style.display = "block";
        // Set boolean
        clock_enabled = false;
    }
}

function transmit() {
    let start_symbol = "11110011";
    let stop_symbol  = stringToBytes('\n')[0];

    const text = input_text.value ;
    if(!clock_enabled)
        span = 1000 / +input_bps.value;

    console.log("Used span: " + span);
    var bytes = [start_symbol];
    const strBytes = stringToBytes(text);
    for(let i = 0; i < strBytes.length; i++) {
        bytes.push(strBytes[i]);
    }
    bytes.push(stop_symbol);

    console.log(bytes);

    transmitBytes(bytes);
}
function transmitBytes(bytes) {
    const bits = toBitArray(bytes);
    // Add bit to reset background
    bits.push("1")
    console.log(bits);

    for(let i = 0; i < bits.length; i++) {
        const bit = bits[i];

        setTimeout(function () {
            var diff = (prev == 0 ? span : Date.now() - prev);
            prev = Date.now()
            delay = span + (span - diff)

            // Tick clock
            if(clock_enabled) {
                var clock_color = "white";
                if (clock.style.backgroundColor.localeCompare("white") == 0) {
                    clock_color = "black";
                }
                clock.style.backgroundColor = clock_color;
            }

            var vis = (bit == '1' ? "white" : "black");
            transmitter.style.background = vis;

            console.log(`${prev} (diff=${diff}, delay=${delay}) Color set to ${vis}`)
        }, span * i)
    }
}
function toBitArray(bytes) {
    let result = [];
    for(let i = 0; i < bytes.length; i++) {
        const str = bytes[i];
        for(let j = 0; j < str.length; j++) {
            result.push(str[j]);
        }
    }
    return result;
}
function toBinary(val, pad_length=8) {
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
