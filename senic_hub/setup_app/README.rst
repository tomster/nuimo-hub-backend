============
Installation
============

1. ``npm install -g react-native-cli``
2. ``npm install``
3. ``react-native run-ios`` or ``react-native run-android``

For more details refer to the React Native `getting started guide <https://facebook.github.io/react-native/docs/getting-started.html#getting-started>`_.

===================================
Test version release using Fastlane
===================================

One time setup
==============

* Install Fabric macOS app from the `Fabric website <https://get.fabric.io/>`_
* Install Fastlane from Fabric macOS app

Android
-------

One time setup
--------------

* Save ``setupapp-release-key.keystore`` file from 1Password entry ``Software/Senic Hub Android release key`` to ``senic_hub/setup_app/android/app/`` directory
* Create a new entry in ``login`` keychain of ``application password`` kind called ``android_keystore``. Password can be copied from 1Password entry ``Software/Senic Hub Android release key``

For each release
----------------

* Increase version numbers in ``senic_hub/setup_app/android/app/build.gradle`` file
* Run ``CRASHLYTICS_BUILD_SECRET=secret_goes_here fastlane beta`` from ``senic_hub/setup_app/android`` directory. ``CRASHLYTICS_BUILD_SECRET`` is available in 1Password entry ``Software/Crashlytics Android Secret build key

iOS
---

TODO
