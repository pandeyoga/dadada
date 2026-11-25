// jsdom (Jest 27) tidak menyediakan TextEncoder/TextDecoder yang dipakai react-router v7.
import { TextEncoder, TextDecoder } from "util";

if (typeof global.TextEncoder === "undefined") global.TextEncoder = TextEncoder;
if (typeof global.TextDecoder === "undefined") global.TextDecoder = TextDecoder;
