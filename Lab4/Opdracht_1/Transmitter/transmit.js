var span = 250;

function transmit() {
    const text = document.getElementById("text").value + "\n";
    const bytes = stringToBytes(text);
    transmitBytes(bytes);
    console.log(bytes)
}
async function transmitBytes(bytes) {
    //Send start
    await sendByte("11110011");
    for(var i = 0; i < bytes.length; i++) {
        await sendByte(bytes[i]);
    }
}
function stringToBytes(str) {
    var utf8 = toUTF8Array(str);
    var bytes = []
    utf8.forEach(item => {
        const bin = toBinary(item);
        console.log(bin)
        bytes.push(bin);
    })
    return bytes;
}
function sendByte(byteStr) {
    var charArray = [];
    for(var i = 0; i < byteStr.length; i++) {
        charArray.push(byteStr[i]);
    }
    return recursiveTransmit(charArray)
}
function recursiveTransmit(chars, i = 0) {

    if(i < chars.length) {
        return sendBit(chars[i]).then(_ => recursiveTransmit(chars, i+1));
    } else {
        return Promise.resolve();
    }
}
function toBinary(val) {
    var bin = val.toString(2);
    var result = "";
    const padding = 8 - bin.length;
    for(var i = 0; i < padding; i++) {
        result += "0";
    }
    result += bin;
    return result;
}

function sendBit(bit) {
    return new Promise(resolve => setTimeout(function() {
        console.log(bit)
        var vis = "black";
        if(bit == '1') {
            vis = "white";
        }
        document.getElementById("transmit-box").style.background = vis;
        console.log("Color set to " + vis + " on " + new Date())
        resolve();
    }, span));
}
function toUTF8Array(str) {
    let utf8 = [];
    for (let i = 0; i < str.length; i++) {
        let charcode = str.charCodeAt(i);
        if (charcode < 0x80) utf8.push(charcode);
        else if (charcode < 0x800) {
            utf8.push(0xc0 | (charcode >> 6),
                      0x80 | (charcode & 0x3f));
        }
        else if (charcode < 0xd800 || charcode >= 0xe000) {
            utf8.push(0xe0 | (charcode >> 12),
                      0x80 | ((charcode>>6) & 0x3f),
                      0x80 | (charcode & 0x3f));
        }
        // surrogate pair
        else {
            i++;
            // UTF-16 encodes 0x10000-0x10FFFF by
            // subtracting 0x10000 and splitting the
            // 20 bits of 0x0-0xFFFFF into two halves
            charcode = 0x10000 + (((charcode & 0x3ff)<<10)
                      | (str.charCodeAt(i) & 0x3ff));
            utf8.push(0xf0 | (charcode >>18),
                      0x80 | ((charcode>>12) & 0x3f),
                      0x80 | ((charcode>>6) & 0x3f),
                      0x80 | (charcode & 0x3f));
        }
    }
    return utf8;
}