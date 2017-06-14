import React from 'react';
import { NetworkInfo } from 'react-native-network-info';
import {
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { isEmulator } from 'react-native-device-info';
import { Button } from 'react-native-elements';
import Screen from './Screen.js';

export default class SetupWelcome extends Screen {
  constructor(props) {
    super(props)

    this.state = {
      networkSSID: null,
    }

    this.setTitle("Welcome")
  }

  componentDidMount() {
    NetworkInfo.getSSID(ssid => {
      this.setState({
        networkSSID: ssid,
      })
    });
  }

  render() {
    return (
      <View style={styles.container}>

        <View>
          <Text style={styles.title}>
            Welcome to Senic Hub
          </Text>
        </View>

        <Text>
          Phone's WiFi SSID: {this.state.networkSSID}
        </Text>

        <View>
          <Button
            buttonStyle={styles.button}
            onPress={ () => this.onContinue() }
            title="Continue" />
        </View>
      </View>
    );
  }

  onContinue() {
    // Bluetooth can't be used in simulators, so we just skip
    // hub onboaring when app is run in the simulator
    if (isEmulator()) {
      this.pushScreen('setup.nuimo')
    }
    else {
      this.pushScreen('setup.hub')
    }
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'column',
    justifyContent: 'space-between',
    padding: 10,
  },
  title: {
    fontSize: 18,
    textAlign: 'center',
    margin: 10,
  },
  button: {
    backgroundColor: '#397af8',
  }
});
